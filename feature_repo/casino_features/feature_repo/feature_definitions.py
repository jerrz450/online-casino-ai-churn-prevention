from datetime import timedelta

from feast import Entity, FeatureView, Field, PushSource, FeatureService
from feast.types import Float32, Int32

# ─── Entity ───────────────────────────────────────────────────────────────────

player = Entity(
    name="player",
    join_keys=["player_id"],
    description="Casino player identified by player_id",
)

# ─── Push Source ──────────────────────────────────────────────────────────────
#  Allows us to push the event data immediately to Redis without needing to go to some data store and read it back in. 
# The worker will subscribe to this source to get the latest features for the player at session end.

player_features_push = PushSource(
    name="player_features_push",
    batch_source=None,
)

# ─── Feature View ─────────────────────────────────────────────────────────────
# Snapshot of player behavioral state captured at each session end.
# Written to Redis via store.push() after every session.
# TTL 2h — features older than this are treated as stale by the worker.

player_stats_fv = FeatureView(
    name="player_stats",
    entities=[player],
    ttl=timedelta(hours=2),
    schema=[
        # Behavioral
        Field(name="emotional_state",               dtype=Int32),   # 0=neutral,1=winning,2=tilting,3=bored,4=recovering
        Field(name="consecutive_losses",            dtype=Int32),
        Field(name="consecutive_wins",              dtype=Int32),
        Field(name="sessions_since_last_big_event", dtype=Int32),
        Field(name="sessions_completed",            dtype=Int32),
        Field(name="bets_in_session",               dtype=Int32),
        Field(name="interventions_received",        dtype=Int32),

        # Financial
        Field(name="session_loss_pct",              dtype=Float32), # (session_start - current) / session_start
        Field(name="bankroll_pct_remaining",        dtype=Float32), # current_bankroll / typical_bankroll
        Field(name="win_rate",                      dtype=Float32), # wins / bets_this_session
        Field(name="avg_bet_ratio",                 dtype=Float32), # avg_bet / typical_bet
        Field(name="net_profit_loss_normalized",    dtype=Float32), # net_pnl / total_wagered

        # Risk
        Field(name="is_at_risk",                    dtype=Int32),   # 0 or 1

        # Player type
        Field(name="player_type_encoded",           dtype=Int32),   # 0=casual,1=grinder,2=whale
    ],
    online=True,
    source=player_features_push,
)

# ─── Feature Service ──────────────────────────────────────────────────────────
# Groups all features consumed by the XGBoost churn model v1.
# Reference this in the worker to avoid listing features individually.

churn_model_v1 = FeatureService(
    name="churn_model_v1",
    features=[player_stats_fv],
)
