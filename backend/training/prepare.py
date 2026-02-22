import json
import sys
import uuid
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import text

from backend.db.connection import get_engine

EMOTIONAL_STATE = {"neutral": 0, "winning": 1, "tilting": 2, "bored": 3, "recovering": 4}

def load_events(engine, run_id=None) -> pd.DataFrame:

    where = f"WHERE run_id = '{run_id}'" if run_id else ""

    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT run_id, player_id, event_type, payload
            FROM raw_training_events {where}
            ORDER BY player_id, (payload->>'timestamp')
        """)).fetchall()
    
    records = []

    for row in rows:
        payload = row.payload if isinstance(row.payload, dict) else json.loads(row.payload)
        records.append({"run_id": str(row.run_id), "player_id": row.player_id, "event_type": row.event_type, **payload})

    return pd.DataFrame(records)


def split_into_sessions(events: pd.DataFrame) -> list:

    sessions, current, prev = [], [], 0

    for _, row in events.iterrows():
        bets = row.get("bets_this_session", 1)

        if bets < prev and current:
            sessions.append(pd.DataFrame(current))
            current = []

        current.append(row)
        prev = bets

    if current:
        sessions.append(pd.DataFrame(current))
    return sessions


def session_snapshot(session: pd.DataFrame, run_id, player_id, session_number, churned) -> dict:

    last = session.iloc[-1]
    wagered = session["bet_amount"].sum()
    net = session["net_result"].sum()
    return {
        "id":                            str(uuid.uuid4()),
        "run_id":                        run_id,
        "player_id":                     int(player_id),
        "player_type":                   None,
        "session_number":                session_number,
        "event_timestamp":               last["timestamp"],
        "churned":                       churned,
        "labeled_at":                    datetime.now(timezone.utc).isoformat(),
        "emotional_state":               EMOTIONAL_STATE.get(str(last.get("emotional_state", "neutral")), 0),
        "consecutive_losses":            int(last.get("consecutive_losses", 0)),
        "consecutive_wins":              int(last.get("consecutive_wins", 0)),
        "session_loss_pct":              float(max(0, -net) / wagered) if wagered else 0.0,
        "bankroll_pct_remaining":        float(last.get("current_bankroll", 0)),
        "win_rate":                      float(session["won"].sum() / len(session)),
        "avg_bet_ratio":                 float(session["bet_amount"].mean()),
        "sessions_completed":            session_number,
        "bets_in_session":               len(session),
        "sessions_since_last_big_event": 0,
        "is_at_risk":                    bool(last.get("is_at_risk", False)),
        "net_profit_loss_normalized":    float(net / wagered) if wagered else 0.0,
        "interventions_received":        0,
    }


def build_snapshots(df: pd.DataFrame) -> list:

    churned_players = set(df[df["event_type"] == "player_churned"]["player_id"].unique())
    bets = df[df["event_type"] == "bet_event"].copy()
    bets["timestamp"] = pd.to_datetime(bets["timestamp"], format="ISO8601", utc=True)
    bets = bets.sort_values("timestamp")

    snapshots = []

    for (run_id, player_id), player_df in bets.groupby(["run_id", "player_id"]):
        sessions = split_into_sessions(player_df)

        for i, session in enumerate(sessions):
            sessions_from_end = len(sessions) - 1 - i
            churned = 1 if player_id in churned_players and sessions_from_end < 2 else 0
            snapshots.append(session_snapshot(session, run_id, player_id, i + 1, churned))

    return snapshots


def run(run_id=None):

    engine = get_engine()
    df = load_events(engine, run_id)

    print(f"{len(df)} events, {df['player_id'].nunique()} players")

    snapshots = build_snapshots(df)
    churned = sum(1 for s in snapshots if s["churned"] == 1)

    print(f"{len(snapshots)} snapshots — churned: {churned}, retained: {len(snapshots) - churned}")

    if not snapshots:
        return

    with engine.begin() as conn:

        conn.execute(text("""
            INSERT INTO player_session_snapshots (
                id, run_id, player_id, player_type, session_number,
                event_timestamp, created,
                emotional_state, consecutive_losses, consecutive_wins,
                session_loss_pct, bankroll_pct_remaining, win_rate, avg_bet_ratio,
                sessions_completed, bets_in_session, sessions_since_last_big_event,
                is_at_risk, net_profit_loss_normalized, interventions_received,
                churned, labeled_at
            ) VALUES (
                :id, :run_id, :player_id, :player_type, :session_number,
                :event_timestamp, NOW(),
                :emotional_state, :consecutive_losses, :consecutive_wins,
                :session_loss_pct, :bankroll_pct_remaining, :win_rate, :avg_bet_ratio,
                :sessions_completed, :bets_in_session, :sessions_since_last_big_event,
                :is_at_risk, :net_profit_loss_normalized, :interventions_received,
                :churned, :labeled_at
            ) ON CONFLICT DO NOTHING
        """), snapshots)

    print(f"Inserted {len(snapshots)} snapshots")

if __name__ == "__main__":

    run(sys.argv[1] if len(sys.argv) > 1 else None)
