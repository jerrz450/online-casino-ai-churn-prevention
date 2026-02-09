"""
Main player simulator orchestrator.

Manages a population of simulated players:
- Creates 100 players with realistic type distribution
- Runs their sessions
- Generates continuous bet stream
- Tracks churn
- Provides interface for agents to query/modify player state
"""

import asyncio
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict

from .player_types import PlayerTypeProfile, PLAYER_TYPES, get_player_type
from .behavior_models import PlayerBehaviorState
from .event_generator import generate_bet_event
from .player_preferences_generator import initialize_player_preferences
from backend.services.domain.player_context_serializer import PlayerContextSerializer
from backend.orchestration.agent_coordinator import get_coordinator
from ..services.domain.knowledge_service import store_player_snapshot, update_outcome

@dataclass
class SimulatedPlayer:

    """A simulated player with type and current state."""

    player_id: int
    player_type: PlayerTypeProfile
    behavior_state: PlayerBehaviorState

    is_active: bool = False
    last_session_end: Optional[datetime] = None
    next_session_start: Optional[datetime] = None
    last_snapshot_id: Optional[str] = None

    created_at: Optional[datetime] = None

    def __post_init__(self):
        
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


class PlayerSimulator:

    """
    Orchestrates simulation of multiple players.

    This is the main entry point for the simulation system.
    """

    def __init__(self, num_players: int = 100):

        self.num_players = num_players
        self.players: Dict[int, SimulatedPlayer] = {}
        self.is_running = False

        self.total_bets_generated = 0
        self.total_interventions_applied = 0
        self.churned_players: List[int] = []

        self.coordinator = get_coordinator(self)

        from backend.services.domain.intervention_evaluator import get_evaluator
        self.evaluator = get_evaluator()

        from backend.services.domain.event_broadcaster import get_broadcaster
        self.broadcaster = get_broadcaster()

    def initialize_players(self):

        """
        Create the player population with realistic distribution. Weighted random choice pattern.

        Distribution (typical for casinos):
        - 10% whales (high value, low volume)
        - 30% grinders (medium value, high volume)
        - 60% casuals (low value, high volume)

        """

        print(f"Initializing {self.num_players} simulated players...")
        
        # So we can sample according to the player type distribution 
        type_distribution = [
            ("whale", 0.10),
            ("grinder", 0.30),
            ("casual", 0.60),
        ]

        players_to_insert = []
        player_ids = []

        for player_id in range(1, self.num_players + 1):

            rand = random.random()
            cumulative = 0.0
            assigned_type = "casual"

            for type_name, probability in type_distribution:

                cumulative += probability

                if rand <= cumulative:
                    assigned_type = type_name
                    break

            player_type = get_player_type(assigned_type)

            behavior_state = PlayerBehaviorState()
            behavior_state.current_bankroll = player_type.typical_bankroll
            behavior_state.session_start_bankroll = player_type.typical_bankroll

            player = SimulatedPlayer(
                player_id=player_id,
                player_type=player_type,
                behavior_state=behavior_state,
            )

            player.next_session_start = datetime.now(timezone.utc) + timedelta(
                seconds=random.randint(0, 10)
            )

            self.players[player_id] = player

            players_to_insert.append({
                "player_id": player_id,
                "player_type": player_type.type_name,
                "ltv": 0.0
            })
            player_ids.append(player_id)

        print(f"== Created {self.num_players} players ==")
        print(f"  - Whales: {sum(1 for p in self.players.values() if p.player_type.type_name == 'whale')}")
        print(f"  - Grinders: {sum(1 for p in self.players.values() if p.player_type.type_name == 'grinder')}")
        print(f"  - Casuals: {sum(1 for p in self.players.values() if p.player_type.type_name == 'casual')}")

        from backend.db.postgres import get_db
        db = get_db()
        db.upsert_players_batch(players_to_insert)

        initialize_player_preferences(player_ids)


    async def start_player_session(self, player: SimulatedPlayer):

        """Start a new session for a player."""

        player.is_active = True
        player.behavior_state.start_new_session()
        player.next_session_start = None

        # print(f"[Player {player.player_id}] Started session (type: {player.player_type.type_name})")


    async def end_player_session(self, player: SimulatedPlayer):

        """End current session and schedule next one."""

        player.last_snapshot_id = await store_player_snapshot(player, outcome='pending')

        player.is_active = False
        player.last_session_end = datetime.now(timezone.utc)

        # Calculate when next session should start based on frequency
        # session_frequency_per_day = how many sessions per day
        hours_between_sessions = 24.0 / player.player_type.session_frequency_per_day

        # Add some variance (+/- 50%)
        actual_hours = hours_between_sessions * random.uniform(0.5, 1.5)

        player.next_session_start = datetime.now(timezone.utc) + timedelta(hours=actual_hours)

        session_stats = player.behavior_state.calculate_session_result()
        print(f"[Player {player.player_id}] Session ended: {session_stats['bets']} bets, €{session_stats['profit_loss']:.2f} P/L, State: {player.behavior_state.emotional_state.value}")

        churned = await self.check_and_handle_churn(player)
        if not churned:
            print(f"[Player {player.player_id}] Did not churn - will return later")


    async def check_and_handle_churn(self, player: SimulatedPlayer) -> bool:

        """
        Check if player should churn and handle it.

        Returns True if player churned, False otherwise.
        """

        should_churn, reason = player.behavior_state.should_churn(
            base_churn_prob=player.player_type.base_churn_probability,
            big_loss_multiplier=player.player_type.churn_after_big_loss_multiplier,
            big_win_multiplier=player.player_type.churn_after_big_win_multiplier,
        )

        if should_churn:

            if player.is_active:
                await self.end_player_session(player)

            player.behavior_state.mark_churned(reason)
            self.churned_players.append(player.player_id)

            if player.last_snapshot_id:
                await update_outcome(player.last_snapshot_id, outcome="churned")

            await self.broadcaster.broadcast_player_churned(player.player_id)

            print(f"[WARNING] [Player {player.player_id}] CHURNED - Reason: {reason.value}")
            print(f" Stats: €{player.behavior_state.net_profit_loss:.2f} P/L, {player.behavior_state.sessions_completed} sessions")

            return True

        return False


    async def generate_bet_for_player(self, player: SimulatedPlayer) -> Optional[dict]:

        """
        Generate next bet for an active player.

        Returns bet event dict or None if session ends.
        """

        if not player.is_active or player.behavior_state.has_churned:
            return None

        # Generate bet event
        bet_event = generate_bet_event(
            player_id=player.player_id,
            player_type=player.player_type,
            behavior_state=player.behavior_state,
        )

        if bet_event is None:
            # Session should end
            await self.end_player_session(player)
            return None

        self.total_bets_generated += 1

        # Add serialized context for Monitor agent
        bet_event["monitor_context"] = PlayerContextSerializer.to_monitor_context(player)

        return bet_event


    async def simulation_tick(self) -> List[dict]:

        """
        Run one simulation tick.

        - Start sessions for players whose time has come
        - Generate bets for all active players
        - Returns list of bet events generated this tick
        """

        now = datetime.now(timezone.utc)
        events = []

        for player in self.players.values():
            # Skip churned players

            if player.behavior_state.has_churned:
                continue

            # Check if it's time to start a new session
            if not player.is_active and player.next_session_start and now >= player.next_session_start:
                await self.start_player_session(player)

            # Generate bet for active players
            if player.is_active:

                bet_event = await self.generate_bet_for_player(player)

                if bet_event:
                    events.append(bet_event)

        return events

    async def run_simulation(self, tick_interval_seconds: float = 1.0):

        """
        Run continuous simulation.

        Generates bet events at specified tick interval.
        """
        
        self.is_running = True
        print(f"\nStarting simulation (tick interval: {tick_interval_seconds}s)")
        print("=" * 60)

        tick_count = 0

        try:

            while self.is_running:

                tick_count += 1
                events = await self.simulation_tick()

                if events:
                    print(f"\n[Tick {tick_count}] Generated {len(events)} bet events")

                    for event in events:
                        await self.broadcaster.broadcast_bet_event(event)

                    await self.coordinator.handle_events(events)

                if tick_count % 50 == 0:
                    self.evaluator.evaluate_recent_interventions(self)

                    active_players = len([p for p in self.players.values() if p.is_active])
                    churned_count = len([p for p in self.players.values() if p.behavior_state.has_churned])

                    await self.broadcaster.broadcast_simulation_stats({
                        "tick": tick_count,
                        "active_players": active_players,
                        "churned_players": churned_count,
                        "total_bets": self.total_bets_generated,
                        "total_interventions": self.total_interventions_applied
                    })

                    # # Sample: show a few events
                    for event in events[:3]:  # Show first 3

                        if event['won']:

                            print(f"  Player {event['player_id']}: €{event['bet_amount']} bet, "
                                  f"WON €{event['payout']:.2f} (net +€{event['net_result']:.2f}), "
                                  f"state: {event['emotional_state']}")

                        else:

                            print(f"  Player {event['player_id']}: €{event['bet_amount']} bet, "
                                  f"LOST (net -€{abs(event['net_result']):.2f}), "
                                  f"state: {event['emotional_state']}")

                    if len(events) > 3:
                        print(f"  ... and {len(events) - 3} more bets")

                if tick_count % 10 == 0:
                    self.print_stats()

                await asyncio.sleep(tick_interval_seconds)

        except KeyboardInterrupt:

            print("\n\nSimulation stopped by user")
            self.is_running = False


    def print_stats(self):

        """Print current simulation statistics."""

        active_players = sum(1 for p in self.players.values() if p.is_active)
        churned_count = len(self.churned_players)
        at_risk = sum(1 for p in self.players.values() if p.behavior_state.is_at_risk)

        print(f"\nSimulation Stats:")
        print(f"   Active sessions: {active_players}/{self.num_players}")
        print(f"   Total bets: {self.total_bets_generated}")
        print(f"   Churned players: {churned_count}")
        print(f"   At-risk players: {at_risk}")
        print(f"   Interventions applied: {self.total_interventions_applied}")


    def get_player(self, player_id: int) -> Optional[SimulatedPlayer]:

        """Get player by ID."""

        return self.players.get(player_id)


    def get_active_players(self) -> List[SimulatedPlayer]:

        """Get all currently active players."""

        return [p for p in self.players.values() if p.is_active]


    def get_at_risk_players(self) -> List[SimulatedPlayer]:

        """Get players flagged as at-risk by Monitor agent."""

        return [p for p in self.players.values() if p.behavior_state.is_at_risk and not p.behavior_state.has_churned]


    def get_player_context(self, player_id: int, context_type: str = "monitor") -> Optional[dict]:
        
        """
        Get serialized context for a player.

        Args:
            player_id: Player ID
            context_type: Type of context ("monitor", "predictor", "designer", "full")

        Returns:
            Serialized context dict or None if player not found
        """

        player = self.get_player(player_id)

        if not player:
            return None

        if context_type == "monitor":
            return PlayerContextSerializer.to_monitor_context(player)
        
        elif context_type == "predictor":
            return PlayerContextSerializer.to_predictor_context(player)
        
        elif context_type == "designer":
            return PlayerContextSerializer.to_designer_context(player)
        
        elif context_type == "full":
            return PlayerContextSerializer.to_full_context(player)
        
        else:
            return PlayerContextSerializer.to_monitor_context(player)


    def get_at_risk_contexts(self) -> List[dict]:

        """Get predictor contexts for all at-risk players."""

        at_risk_players = self.get_at_risk_players()
        return [PlayerContextSerializer.to_predictor_context(p) for p in at_risk_players]


    def apply_intervention(self, player_id: int, intervention_type: str, amount: float) -> bool:
        
        """
        Apply an intervention to a player (called by Executor agent).

        Returns True if successful, False if player not found or already churned.
        """

        player = self.get_player(player_id)

        if not player or player.behavior_state.has_churned:
            return False

        player.behavior_state.apply_intervention_effect(intervention_type, amount)
        self.total_interventions_applied += 1

        print(f"[OK] [Player {player_id}] Intervention applied: {intervention_type} €{amount}")

        return True

async def run_basic_simulation(num_players : int = 100):

    simulator = PlayerSimulator(num_players=num_players)
    simulator.initialize_players ()
    await simulator.run_simulation(tick_interval_seconds=2.0)

if __name__ == "__main__":

    import sys
    import platform

    if len(sys.argv) > 1:
        num_players = int(sys.argv[1])
    else:
        num_players = 100

    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(run_basic_simulation(num_players))
