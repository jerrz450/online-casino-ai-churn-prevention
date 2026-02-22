"""
Centralized Redis key definitions.
All queue names, cache prefixes, and key patterns live here.
"""


class RedisKeys:

    # ── Simulation run tracking ──────────────────────────────────────────────
    CURRENT_RUN_ID      = "run:current_id"       # UUID of the active simulation run

    # ── Ingestion ────────────────────────────────────────────────────────────
    INGEST_EVENTS       = "ingest:events"        # raw event queue from simulator

    # ── Decisioning ──────────────────────────────────────────────────────────
    DECISIONS_QUEUE     = "decisions:queue"      # events pending churn scoring

    # ── Feature cache ────────────────────────────────────────────────────────
    FEATURES_PREFIX     = "features:{player_id}" # Feast online store key pattern

    # ── Cooldowns ────────────────────────────────────────────────────────────
    COOLDOWN_PREFIX     = "cooldown:{player_id}" # intervention cooldown flag

    # ── Budget caps ──────────────────────────────────────────────────────────
    BUDGET_PREFIX       = "budget:{player_id}"   # monthly bonus spend tracker

    # ── Dynamic config (written by analyst agent, read by decision_worker) ───
    CHURN_THRESHOLD     = "config:churn_threshold"  # float, overrides default 0.3
    MODEL_RELOAD        = "config:model_reload"     # "1" triggers hot reload
    TRAIN_CONFIG        = "config:train_params"     # JSON dict of XGBoost hyperparams

    @staticmethod
    def player_state(player_id: int) -> str:
        return f"player:state:{player_id}"

    @staticmethod
    def features(player_id: int) -> str:
        return f"features:{player_id}"

    @staticmethod
    def cooldown(player_id: int) -> str:
        return f"cooldown:{player_id}"

    @staticmethod
    def budget(player_id: int) -> str:
        return f"budget:{player_id}"
