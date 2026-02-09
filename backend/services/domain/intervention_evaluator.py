from datetime import datetime, timedelta, timezone
from backend.db.postgres import get_db

class InterventionEvaluator:

    def __init__(self):
        self.db = get_db()

    def evaluate_intervention(self, player_id: int, intervention_id: str, player_churned: bool, days_since: int):

        if days_since < 7:
            return

        if player_churned:
            outcome = "failed"
        else:
            outcome = "success"

        self.db.update_intervention_outcome(intervention_id, outcome)

        print(f"[Evaluator] Intervention {intervention_id} for Player {player_id}: {outcome.upper()}")

    def evaluate_recent_interventions(self, simulator):

        from sqlalchemy import text
        from backend.db.connection import get_engine

        engine = get_engine()

        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

        query = text("""
            SELECT id, player_id, timestamp
            FROM interventions
            WHERE outcome IS NULL
            AND timestamp < :seven_days_ago
        """)

        with engine.begin() as conn:
            result = conn.execute(query, {"seven_days_ago": seven_days_ago})
            pending_interventions = result.fetchall()

        for row in pending_interventions:
            intervention_id = row[0]
            player_id = row[1]
            timestamp = row[2]

            player = simulator.players.get(player_id)

            if not player:
                continue

            days_since = (datetime.now(timezone.utc) - timestamp).days
            player_churned = player.behavior_state.has_churned

            self.evaluate_intervention(player_id, str(intervention_id), player_churned, days_since)

_evaluator = None

def get_evaluator():
    global _evaluator
    if _evaluator is None:
        _evaluator = InterventionEvaluator()
    return _evaluator
