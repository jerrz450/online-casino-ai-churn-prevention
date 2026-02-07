import asyncio
from typing import List, Dict, Any, TYPE_CHECKING
from backend.agents.monitor_agent import MonitorAgent
from backend.agents.predictor_agent import get_predictor

class AgentCoordinator:

    def __init__(self, simulator):

        self.simulator = simulator
        self.monitor = MonitorAgent()
        self.predictor = get_predictor()

    async def handle_events(self, events: List[Dict[str, Any]]) -> None:

        if not events:
            return

        flagged_player_ids = await self.monitor.analyze_events(events)

        if not flagged_player_ids:
            return

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

_coordinator = None

def get_coordinator(simulator = None) -> AgentCoordinator:

    global _coordinator

    if _coordinator is None:
        
        if simulator is None:
            raise ValueError("Simulator must be provided on first call")
        
        _coordinator = AgentCoordinator(simulator)

    return _coordinator
