from decimal import Decimal

from langchain_core.tools import tool
from sqlalchemy import text

from backend.db.connection import get_engine


def _to_dict(row) -> dict:
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in row._mapping.items()}


@tool
def get_score_distribution() -> dict:
    
    """Churn score stats from the last 24h of decisions: avg, p50, p90, total scored, offers sent."""

    with get_engine().begin() as conn:

        row = conn.execute(text("""
            SELECT
                ROUND(AVG(churn_score)::numeric, 3)                                          AS avg_score,
                ROUND(percentile_cont(0.5) WITHIN GROUP (ORDER BY churn_score)::numeric, 3)  AS p50_score,
                ROUND(percentile_cont(0.9) WITHIN GROUP (ORDER BY churn_score)::numeric, 3)  AS p90_score,
                COUNT(*)                                                                      AS total_scored,
                COUNT(*) FILTER (WHERE action = 'offer_sent')                                AS offers_sent
            FROM decisions
            WHERE timestamp > NOW() - INTERVAL '24 hours'
        """)).first()

    return _to_dict(row) if row else {}


@tool
def get_false_positive_rate() -> dict:

    """Players flagged (offer_sent) whose most recent session snapshot shows churned=0."""

    with get_engine().begin() as conn:

        row = conn.execute(text("""
            WITH latest_flagged AS (
                SELECT DISTINCT ON (player_id) player_id
                FROM decisions
                WHERE action = 'offer_sent'
                ORDER BY player_id, timestamp DESC
            ),
            latest_snapshots AS (
                SELECT DISTINCT ON (player_id) player_id, churned
                FROM player_session_snapshots
                ORDER BY player_id, event_timestamp DESC
            )
            SELECT
                COUNT(*)                                                              AS total_flagged,
                COUNT(*) FILTER (WHERE ls.churned = 0 OR ls.churned IS NULL)         AS false_positives,
                ROUND(
                    100.0 * COUNT(*) FILTER (WHERE ls.churned = 0 OR ls.churned IS NULL)
                    / NULLIF(COUNT(*), 0), 1
                )                                                                     AS false_positive_pct
            FROM latest_flagged lf
            LEFT JOIN latest_snapshots ls ON ls.player_id = lf.player_id
                                
        """)).first()

    return _to_dict(row) if row else {}


@tool
def get_segment_performance() -> list:

    """Score distribution and flag rate by player type (whale/grinder/casual) over last 24h."""

    with get_engine().begin() as conn:

        rows = conn.execute(text("""
            SELECT
                p.player_type,
                COUNT(*)                                                                      AS total_scored,
                COUNT(*) FILTER (WHERE d.action = 'offer_sent')                              AS flagged,
                ROUND(AVG(d.churn_score)::numeric, 3)                                        AS avg_score,
                ROUND(
                    100.0 * COUNT(*) FILTER (WHERE d.action = 'offer_sent')
                    / NULLIF(COUNT(*), 0), 1
                )                                                                             AS flag_rate_pct
            FROM decisions d
            JOIN players p ON p.player_id = d.player_id
            WHERE d.timestamp > NOW() - INTERVAL '24 hours'
            GROUP BY p.player_type
            ORDER BY avg_score DESC
        """)).fetchall()

    return [_to_dict(r) for r in rows]


@tool
def get_model_metrics() -> dict:

    """Last trained model's AUC, tree count, and feature importances."""

    import json, os
    import xgboost as xgb
    from backend.training.features import FEATURES

    metrics_path = "models/metrics.json"
    model_path = "models/churn_v1.json"

    if os.path.exists(metrics_path):
        with open(metrics_path) as f:
            return json.load(f)

    if not os.path.exists(model_path):
        return {"status": "not_available", "reason": "model has not been trained yet"}

    model = xgb.XGBClassifier()
    model.load_model(model_path)
    return {
        "auc": "unknown — retrain to generate",
        "feature_importances": dict(zip(FEATURES, model.feature_importances_.tolist())),
    }


@tool
def get_intervention_outcomes() -> dict:

    """Breakdown of intervention outcomes: success, failed, pending counts."""

    with get_engine().begin() as conn:
        
        rows = conn.execute(text("""
            SELECT COALESCE(outcome, 'pending') AS outcome, COUNT(*) AS count
            FROM interventions
            GROUP BY outcome
            ORDER BY count DESC
                                 
        """)).fetchall()

    return {r.outcome: r.count for r in rows}
