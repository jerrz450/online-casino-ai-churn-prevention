import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

import pandas as pd
import xgboost as xgb
from sqlalchemy import text

from backend.db.connection import get_engine
from backend.db.redis_client import get_redis
from backend.db.redis_keys import RedisKeys
from backend.training.features import FEATURES, EMOTIONAL_STATE

logger = logging.getLogger(__name__)

MODEL_PATH = "models/churn_v1.json"
DEFAULT_THRESHOLD = 0.3
SCORE_EVERY_N_BETS = 10
BATCH_WINDOW = 0.05

engine = get_engine()

def load_model() -> xgb.XGBClassifier:

    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)
    return model


async def update_state(redis, player_id: int, event: dict) -> dict:

    key = RedisKeys.player_state(player_id)

    raw = await redis.hgetall(key)
    state = dict(raw) if raw else {}

    bets_this_session = int(event.get("bets_this_session", 1))
    prev_bets = int(state.get("bets_this_session", 0))

    if bets_this_session < prev_bets and prev_bets > 0:
        
        state.update({
            "sessions_completed": str(int(state.get("sessions_completed", 0)) + 1),
            "bets_in_session": "0",
            "session_total_wagered": "0",
            "session_net_pnl": "0",
            "session_wins": "0",
        })

    bets_in_session = int(state.get("bets_in_session", 0)) + 1
    total_wagered = float(state.get("session_total_wagered", 0)) + float(event.get("bet_amount", 0))
    net_pnl = float(state.get("session_net_pnl", 0)) + float(event.get("net_result", 0))
    wins = int(state.get("session_wins", 0)) + (1 if event.get("won") else 0)

    state.update({
        "bets_in_session": str(bets_in_session),
        "session_total_wagered": str(total_wagered),
        "session_net_pnl": str(net_pnl),
        "session_wins": str(wins),
        "bets_this_session": str(bets_this_session),
        "emotional_state": str(EMOTIONAL_STATE.get(str(event.get("emotional_state", "neutral")), 0)),
        "consecutive_losses": str(event.get("consecutive_losses", 0)),
        "consecutive_wins": str(event.get("consecutive_wins", 0)),
        "current_bankroll": str(event.get("current_bankroll", 0)),
        "is_at_risk": str(1 if event.get("is_at_risk") else 0),
    })

    await redis.hset(key, mapping=state)
    await redis.expire(key, 86400)
    return state


def build_feature_row(state: dict) -> dict:

    bets = int(state.get("bets_in_session", 1)) or 1
    wagered = float(state.get("session_total_wagered", 0))
    net = float(state.get("session_net_pnl", 0))
    wins = int(state.get("session_wins", 0))

    return {
        "emotional_state": float(state.get("emotional_state", 0)),
        "consecutive_losses": float(state.get("consecutive_losses", 0)),
        "consecutive_wins": float(state.get("consecutive_wins", 0)),
        "session_loss_pct": max(0, -net) / wagered if wagered else 0.0,
        "bankroll_pct_remaining": float(state.get("current_bankroll", 0)),
        "win_rate": wins / bets,
        "avg_bet_ratio": wagered / bets,
        "sessions_completed": float(state.get("sessions_completed", 0)),
        "bets_in_session": float(bets),
        "sessions_since_last_big_event": 0.0,
        "is_at_risk": float(state.get("is_at_risk", 0)),
        "net_profit_loss_normalized": net / wagered if wagered else 0.0,
        "interventions_received": float(state.get("interventions_received", 0)),
    }


def insert_decisions(decisions: list[dict]):

    with engine.begin() as conn:

        conn.execute(text("""
            INSERT INTO decisions (id, player_id, churn_score, model_version, feature_timestamp, action, reason)
            VALUES (:id, :player_id, :churn_score, :model_version, :feature_timestamp, :action, :reason)
        """), decisions)


async def run():

    redis = await get_redis()
    model = load_model()

    logger.info(f"Model loaded — threshold={DEFAULT_THRESHOLD}, score_every={SCORE_EVERY_N_BETS} bets")
    logger.info(f"Listening on {RedisKeys.DECISIONS_QUEUE}")

    pending: dict[int, dict] = {}
    last_scored = asyncio.get_running_loop().time()

    while True:

        result = await redis.blpop(RedisKeys.DECISIONS_QUEUE, timeout=BATCH_WINDOW)

        if result:

            _, raw = result
            event = json.loads(raw)
            player_id = int(event.get("player_id"))
            state = await update_state(redis, player_id, event)

            if int(state.get("bets_in_session", 0)) % SCORE_EVERY_N_BETS == 0:
                pending[player_id] = state

        if await redis.getdel(RedisKeys.MODEL_RELOAD):

            model = load_model()
            logger.info("Model hot-reloaded from disk")

        now = asyncio.get_running_loop().time()

        if pending and (now - last_scored >= BATCH_WINDOW):

            threshold_str = await redis.get(RedisKeys.CHURN_THRESHOLD)
            threshold = float(threshold_str) if threshold_str else DEFAULT_THRESHOLD

            player_ids = list(pending.keys())

            features_df = pd.DataFrame([build_feature_row(pending[pid]) for pid in player_ids], columns=FEATURES)
            scores = model.predict_proba(features_df)[:, 1]

            now_iso = datetime.now(timezone.utc).isoformat()
            decisions = []

            for pid, score in zip(player_ids, scores):

                offer = score >= threshold

                decisions.append({
                    "id": str(uuid.uuid4()),
                    "player_id": pid,
                    "churn_score": float(score),
                    "model_version": "churn_v1",
                    "feature_timestamp": now_iso,
                    "action": "offer_sent" if offer else "no_action",
                    "reason": f"score={score:.3f}",
                })

                if offer:
                    logger.info(f"ALERT player={pid} score={score:.3f} → offer_sent")

            await asyncio.to_thread(insert_decisions, decisions)

            logger.info(f"Scored {len(decisions)} players | threshold={threshold:.2f}")

            pending.clear()
            last_scored = now


if __name__ == "__main__":
    asyncio.run(run())