import asyncio
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict

from .player_types import PlayerTypeProfile, get_player_type
from .behavior_models import PlayerBehaviorState
from .event_generator import generate_bet_event, get_time_between_bets
from .db import upsert_players_batch

@dataclass
class SimulatedPlayer:

    player_id:   int
    player_type: PlayerTypeProfile
    behavior_state: PlayerBehaviorState

    is_active:           bool              = False
    next_session_start:  Optional[datetime] = None
    next_bet_at:         Optional[datetime] = None
    session_target_bets: int               = 0

    # Training mode: synthetic clock tracking
    sim_current_time:    Optional[datetime] = None  # current simulated wall time


class PlayerSimulator:

    def __init__(
        self,
        num_players: int = 50,
        *,
        mode: str = "inference",   # "inference" | "training"
        event_queue=None,
    ):
        self.num_players  = num_players
        self.mode         = mode
        self.training     = mode == "training"
        self.players:  Dict[int, SimulatedPlayer] = {}
        self.is_running   = False
        self.event_queue  = event_queue

        self.total_bets_generated        = 0
        self.total_interventions_applied = 0
        self.churned_players: List[int]  = []


    def initialize_players(self):

        print(f"Initializing {self.num_players} players...")

        type_names = random.choices(
            ["whale", "grinder", "casual"],
            weights=[0.10, 0.30, 0.60],
            k=self.num_players,
        )

        players_to_insert = []
        
        for player_id, type_name in enumerate(type_names, start=1):

            player_type = get_player_type(type_name)
            state = PlayerBehaviorState(
                current_bankroll=player_type.typical_bankroll,
                session_start_bankroll=player_type.typical_bankroll,
            )

            # Training: stagger join dates over the past 30-90 days
            sim_start = (
                datetime.now(timezone.utc) - timedelta(days=random.randint(30, 90))
                if self.training else None
            )

            player = SimulatedPlayer(
                player_id=player_id,
                player_type=player_type,
                behavior_state=state,
                next_session_start=datetime.now(timezone.utc) + timedelta(seconds=random.randint(0, 30)),
                sim_current_time=sim_start,
            )

            self.players[player_id] = player
            players_to_insert.append({"player_id": player_id, "player_type": type_name, "ltv": 0.0})

        upsert_players_batch(players_to_insert)

        from .player_preferences_generator import initialize_player_preferences
        initialize_player_preferences(list(self.players.keys()))

        counts = {t: type_names.count(t) for t in ["whale", "grinder", "casual"]}
        print(f"  Whales: {counts['whale']}  Grinders: {counts['grinder']}  Casuals: {counts['casual']}")


    def _start_session(self, player: SimulatedPlayer):

        player.is_active = True
        player.next_session_start  = None
        player.next_bet_at = datetime.now(timezone.utc)
        player.behavior_state.start_new_session()

        base = player.player_type.avg_bets_per_session
        player.session_target_bets = int(base * random.uniform(0.5, 1.5))


    async def _end_session(self, player: SimulatedPlayer):

        player.is_active   = False
        player.next_bet_at = None

        player.behavior_state.check_boredom(player.player_type.boredom_threshold_sessions)

        should_churn, reason = player.behavior_state.should_churn(
            base_churn_prob=player.player_type.base_churn_probability,
            big_loss_multiplier=player.player_type.churn_after_big_loss_multiplier,
            big_win_multiplier=player.player_type.churn_after_big_win_multiplier,
        )

        if should_churn:
            player.behavior_state.mark_churned(reason)
            self.churned_players.append(player.player_id)

            if self.event_queue is not None:
                await self.event_queue.put({
                    "type": "player_churned",
                    "player_id": player.player_id,
                    "reason": reason.value,
                })

            print(f"[CHURN] Player {player.player_id}: {reason.value}")

        else:
            player.next_session_start = (
                datetime.now(timezone.utc) + timedelta(seconds=random.randint(3, 45))
            )

            # Training: advance simulated clock by realistic inter-session gap
            if self.training and player.sim_current_time is not None:
                gap_hours = 24 / player.player_type.session_frequency_per_day
                noise     = random.uniform(0.5, 2.0)
                player.sim_current_time += timedelta(hours=gap_hours * noise)


    def _generate_bet(self, player: SimulatedPlayer) -> Optional[dict]:

        state = player.behavior_state

        if state.current_bankroll <= 0 or state.bets_this_session >= player.session_target_bets:
            return None

        sim_ts = player.sim_current_time if self.training else None
        event  = generate_bet_event(player.player_id, player.player_type, state, timestamp=sim_ts)
        if event is None:
            return None

        event["type"] = "bet_event"
        self.total_bets_generated += 1

        delay = get_time_between_bets(state)
        player.next_bet_at = datetime.now(timezone.utc) + timedelta(seconds=delay)

        return event


    async def _tick(self) -> List[dict]:

        now    = datetime.now(timezone.utc)
        events = []

        for player in self.players.values():
            if player.behavior_state.has_churned:
                continue

            if not player.is_active and player.next_session_start and now >= player.next_session_start:
                self._start_session(player)

            if player.is_active and player.next_bet_at and now >= player.next_bet_at:
                event = self._generate_bet(player)

                if event is None:
                    await self._end_session(player)
                else:
                    events.append(event)

        return events


    async def run_simulation(self, tick_interval_seconds: float = 0.05, max_events: Optional[int] = None):

        self.is_running = True

        print(f"Simulation running (tick={tick_interval_seconds}s)")

        try:
            while self.is_running:
                if max_events and self.total_bets_generated >= max_events:
                    break

                events = await self._tick()

                if events and self.event_queue is not None:
                    for event in events:
                        await self.event_queue.put(event)

                await asyncio.sleep(tick_interval_seconds)

        except asyncio.CancelledError:

            self.is_running = False


    def get_player(self, player_id: int) -> Optional[SimulatedPlayer]:

        return self.players.get(player_id)

    def get_active_players(self) -> List[SimulatedPlayer]:

        return [p for p in self.players.values() if p.is_active]

    def get_at_risk_players(self) -> List[SimulatedPlayer]:

        return [p for p in self.players.values()
                if p.behavior_state.is_at_risk and not p.behavior_state.has_churned]

    def apply_intervention(self, player_id: int, intervention_type: str, amount: float) -> bool:

        player = self.get_player(player_id)

        if not player or player.behavior_state.has_churned:
            return False
        
        player.behavior_state.apply_intervention(intervention_type, amount)
        self.total_interventions_applied += 1

        return True
