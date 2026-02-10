from datetime import datetime
from typing import Optional

class EventBroadcaster:

    def __init__(self):
        self.manager = None

    def set_manager(self, manager):
        self.manager = manager

    async def broadcast_monitor_flag(self, player_ids: list):
        if not self.manager:
            return

        await self.manager.broadcast({
            "type": "monitor_flag",
            "timestamp": datetime.utcnow().isoformat(),
            "player_ids": player_ids,
            "count": len(player_ids)
        })

    async def broadcast_intervention(self, player_id: int, intervention: dict, risk_score: float):
        if not self.manager:
            return

        await self.manager.broadcast({
            "type": "intervention_designed",
            "timestamp": datetime.utcnow().isoformat(),
            "player_id": player_id,
            "risk_score": risk_score,
            "intervention_type": intervention.get("intervention_type"),
            "amount": intervention.get("amount"),
            "message": intervention.get("message"),
            "reasoning": intervention.get("reasoning")
        })

    async def broadcast_bet_event(self, bet_event: dict):
        if not self.manager:
            return

        await self.manager.broadcast({
            "type": "bet_event",
            "timestamp": datetime.utcnow().isoformat(),
            "player_id": bet_event.get("player_id"),
            "bet_amount": bet_event.get("bet_amount"),
            "won": bet_event.get("won"),
            "payout": bet_event.get("payout"),
            "emotional_state": bet_event.get("emotional_state")
        })

    async def broadcast_bet_batch(self, bet_events: list):
        if not self.manager:
            return

        await self.manager.broadcast({
            "type": "bet_batch",
            "timestamp": datetime.utcnow().isoformat(),
            "count": len(bet_events),
            "events": [
                {
                    "player_id": event.get("player_id"),
                    "bet_amount": event.get("bet_amount"),
                    "won": event.get("won"),
                    "payout": event.get("payout"),
                    "emotional_state": event.get("emotional_state")
                }
                for event in bet_events
            ]
        })

    async def broadcast_player_churned(self, player_id: int):
        if not self.manager:
            return

        await self.manager.broadcast({
            "type": "player_churned",
            "timestamp": datetime.utcnow().isoformat(),
            "player_id": player_id
        })

    async def broadcast_simulation_stats(self, stats: dict):
        if not self.manager:
            return

        await self.manager.broadcast({
            "type": "simulation_stats",
            "timestamp": datetime.utcnow().isoformat(),
            **stats
        })

    async def broadcast_initial_players(self, player_ids: list):
        if not self.manager:
            return

        await self.manager.broadcast({
            "type": "initial_players",
            "timestamp": datetime.utcnow().isoformat(),
            "player_ids": player_ids
        })

_broadcaster = None

def get_broadcaster():
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = EventBroadcaster()
    return _broadcaster
