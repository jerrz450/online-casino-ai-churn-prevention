import asyncio
from typing import List, Dict, Any, TYPE_CHECKING
from backend.agents.monitor_agent import MonitorAgent
from backend.agents.predictor_agent import get_predictor
from backend.agents.designer_agent import DesignerAgent
from backend.db.postgres import get_db

class AgentCoordinator:

    def __init__(self, simulator):

        self.simulator = simulator
        self.monitor = MonitorAgent()
        self.predictor = get_predictor()
        self.designer = DesignerAgent()
        self.db = get_db()

    async def handle_events(self, events: List[Dict[str, Any]]) -> None:

        if not events:
            return

        flagged_player_ids = await self.monitor.analyze_events(events)

        if not flagged_player_ids:
            return

        flagged_player_ids = list(set(flagged_player_ids))
        print(f"[Coordinator] Processing {len(flagged_player_ids)} unique flagged players")

        tasks = []
        players = []

        for player_id in flagged_player_ids:
            player = self.simulator.players.get(player_id)
            
            if player:
                tasks.append(self.predictor.calculate_risk(player))
                players.append(player)

        if not tasks:
            return

        risk_scores = await asyncio.gather(*tasks)

        for player, risk_score in zip(players, risk_scores):

            if risk_score > 0.7:

                print(f"[Coordinator] Player {player.player_id} HIGH RISK ({risk_score:.2f}) - needs intervention")

                cooldown_check = self.db.check_cooldown(player.player_id, hours=6)
                if not cooldown_check["can_send"]:
                    last_sent = cooldown_check.get("last_sent_at", "unknown")
                    print(f"[Coordinator] Player {player.player_id} in cooldown (last sent: {last_sent}) - skipping intervention")
                    continue

                print(f"[Coordinator] Player {player.player_id} passed cooldown check - designing intervention")

                import random
                if random.random() > 0.7:
                    print(f"[Coordinator] Player {player.player_id} not selected for intervention (resource constraints)")
                    continue

                from backend.services.domain.player_context_serializer import PlayerContextSerializer

                player_context = PlayerContextSerializer.to_designer_context(player)

                intervention = await self.designer.design_intervention(player_context, risk_score)

                if intervention:

                    print(f"[Coordinator] Designed intervention: {intervention}")

                    from backend.services.domain.event_broadcaster import get_broadcaster
                    await get_broadcaster().broadcast_intervention(player.player_id, intervention, risk_score)

                    intervention_id = self.db.create_intervention(
                        player_id=player.player_id,
                        risk_score=risk_score,
                        intervention_type=intervention.get("intervention_type", "unknown"),
                        amount=intervention.get("amount", 0.0),
                        message=intervention.get("message", "")
                    )

                    print(f"[Coordinator] Stored intervention {intervention_id} for Player {player.player_id}")

_coordinator = None

def get_coordinator(simulator = None) -> AgentCoordinator:

    global _coordinator

    if _coordinator is None or (simulator is not None and _coordinator.simulator is not simulator):

        if simulator is None:
            raise ValueError("Simulator must be provided on first call")

        _coordinator = AgentCoordinator(simulator)

    return _coordinator
