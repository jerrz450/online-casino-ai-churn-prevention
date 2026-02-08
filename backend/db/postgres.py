from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import text
from backend.db.connection import get_engine

class Database:

    def upsert_player(self, player_id: int, player_type: str, ltv: float):

        engine = get_engine()

        query = text("""
            INSERT INTO players (player_id, player_type, ltv, created_at)
            VALUES (:player_id, :player_type, :ltv, NOW())
            ON CONFLICT (player_id) DO UPDATE
            SET player_type = :player_type, ltv = :ltv
        """)

        with engine.begin() as conn:
            conn.execute(query, {"player_id": player_id, "player_type": player_type, "ltv": ltv})

    def upsert_players_batch(self, players: List[dict]):

        engine = get_engine()

        query = text("""
            INSERT INTO players (player_id, player_type, ltv, created_at, last_active)
            VALUES (:player_id, :player_type, :ltv, NOW(), NOW())
            ON CONFLICT (player_id) DO UPDATE
            SET player_type = EXCLUDED.player_type, ltv = EXCLUDED.ltv, last_active = NOW()
        """)

        with engine.begin() as conn:
            conn.execute(query, players)

    def create_intervention(
        self,
        player_id: int,
        risk_score: float,
        intervention_type: str,
        amount: float,
        message: str
    ) -> UUID:
        
        engine = get_engine()
        
        intervention_id = uuid4()
        
        query = text("""
            INSERT INTO interventions (id, player_id, risk_score, intervention_type, amount, message)
            VALUES (:id, :player_id, :risk_score, :intervention_type, :amount, :message)
        """)

        with engine.begin() as conn:
            conn.execute(query, {
                "id": intervention_id,
                "player_id": player_id,
                "risk_score": risk_score,
                "intervention_type": intervention_type,
                "amount": amount,
                "message": message
            })

        return intervention_id

    def update_intervention_outcome(self, intervention_id: UUID, outcome: str):
        
        engine = get_engine()

        query = text("""
            UPDATE interventions
            SET outcome = :outcome, outcome_measured_at = NOW()
            WHERE id = :id
        """)

        with engine.begin() as conn:
            conn.execute(query, {"outcome": outcome, "id": intervention_id})

    def get_player_intervention_history(self, player_id: int, limit: int = 5) -> List[dict]:
        
        engine = get_engine()

        query = text("""
            SELECT intervention_type, amount, outcome, timestamp
            FROM interventions
            WHERE player_id = :player_id
            ORDER BY timestamp DESC
            LIMIT :limit
        """)

        with engine.begin() as conn:

            result = conn.execute(query, {"player_id": player_id, "limit": limit})
            return [dict(row._mapping) for row in result]

    def get_intervention_success_rate(self, intervention_type: str) -> float:

        engine = get_engine()

        query = text("""
            SELECT COALESCE(AVG(CASE WHEN outcome = 'retained' THEN 1.0 ELSE 0.0 END), 0)
            FROM interventions
            WHERE intervention_type = :intervention_type AND outcome IS NOT NULL
        """)

        with engine.begin() as conn:

            result = conn.execute(query, {"intervention_type": intervention_type})
            return float(result.scalar() or 0.0)

    def get_player_preferences(self, player_id: int) -> Optional[dict]:

        engine = get_engine()
        query = text("SELECT * FROM player_preferences WHERE player_id = :player_id")

        with engine.begin() as conn:
            result = conn.execute(query, {"player_id": player_id})
            row = result.first()

            return dict(row._mapping) if row else None

    def check_cooldown(self, player_id: int, hours: int = 6) -> dict:

        engine = get_engine()

        query = text("SELECT last_intervention_at FROM player_preferences WHERE player_id = :player_id")

        with engine.begin() as conn:
            result = conn.execute(query, {"player_id": player_id})
            row = result.first()

            if not row:
                return {"can_send": True, "reason": "player_not_found"}

            if not row.last_intervention_at:
                return {"can_send": True, "reason": "no_previous_intervention"}

            elapsed = (datetime.now() - row.last_intervention_at).total_seconds() / 3600
            can_send = elapsed >= hours

            return {
                "can_send": can_send,
                "reason": "cooldown_passed" if can_send else "in_cooldown",
                "hours_since_last": round(elapsed, 2)
            }
        

    def create_monitor_event(self, player_id: int, decision: str, decision_source: str, player_context: dict | str):                               
                                                                                                                                                                            
        engine = get_engine()                                                                                                                                         
                                                                                                                                                                            
        query = text("""                                                                                                                                              
            INSERT INTO monitor_events (id, player_id, timestamp, decision, decision_source, player_context)                                      
            VALUES (:id, :player_id, NOW(), :decision, :decision_source, :player_context)                                                        
        """)                                                                                                                                                          
                                                                                                                                                                            
        with engine.begin() as conn:                                                                                                                                  
            conn.execute(query, {                                                                                                                                     
                "id": uuid4(),                                                                                                                                        
                "player_id": player_id,                                                                                                                               
                "decision": decision,                                                                                                                                 
                "decision_source": decision_source,                                                                                                                   
                "player_context": player_context                                                                                                                    

            })                

    def update_intervention_sent(self, player_id: int, amount: float):

        engine = get_engine()

        query = text("""
            INSERT INTO player_preferences (player_id, monthly_bonus_total, last_intervention_at)
            VALUES (:player_id, :amount, NOW())
            ON CONFLICT (player_id) DO UPDATE
            SET monthly_bonus_total = COALESCE(player_preferences.monthly_bonus_total, 0) + :amount,
                last_intervention_at = NOW()
        """)

        with engine.begin() as conn:
            conn.execute(query, {"player_id": player_id, "amount": amount})

_db = None

def get_db() -> Database:

    global _db

    if _db is None:
        _db = Database()
        
    return _db
