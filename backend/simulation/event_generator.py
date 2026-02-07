"""
Generates realistic bet events for simulated players.

Takes player type + current behavioral state and generates:
- Bet amounts (adjusted for emotional state)
- Outcomes (win/loss with realistic house edge)
- Timing (delay between bets)
"""

import random
from datetime import datetime, timedelta
from typing import Optional

from .player_types import PlayerTypeProfile
from .behavior_models import PlayerBehaviorState, EmotionalState


# Realistic casino house edge (RTP = Return to Player)
# Slots typically have 92-97% RTP, meaning house edge of 3-8%
HOUSE_EDGE = 0.05  # 5% house edge = 95% RTP


class BetEventGenerator:

    """Generates realistic bet events for a player."""

    def __init__(self, player_type: PlayerTypeProfile, behavior_state: PlayerBehaviorState):

        self.player_type = player_type
        self.behavior_state = behavior_state

    def generate_bet_amount(self) -> float:

        """
        Generate a bet amount based on player type and emotional state.

        Emotional state affects sizing:
        - NEUTRAL: typical bet with some variance
        - WINNING: slight increase (confidence)
        - TILTING: aggressive increase (chasing losses)
        - BORED: slight decrease (losing interest)
        - RECOVERING: back to normal

        """
        base_bet = self.player_type.typical_bet

        # Apply emotional state modifiers
        if self.behavior_state.emotional_state == EmotionalState.NEUTRAL:
            # Normal variance around typical bet (±30%)
            multiplier = random.uniform(0.7, 1.3)

        elif self.behavior_state.emotional_state == EmotionalState.WINNING:
            # Slightly higher when winning (confidence)
            multiplier = random.uniform(1.0, 1.4)

        elif self.behavior_state.emotional_state == EmotionalState.TILTING:
            # TILTING = danger zone for Monitor agent
            multiplier = self.player_type.tilt_bet_multiplier
            # Add some chaos
            multiplier *= random.uniform(0.9, 1.5)

        elif self.behavior_state.emotional_state == EmotionalState.BORED:
            # Smaller bets when bored (not engaged)
            multiplier = random.uniform(0.5, 0.9)

        elif self.behavior_state.emotional_state == EmotionalState.RECOVERING:
            # Back to normal after intervention
            multiplier = random.uniform(0.8, 1.2)

        else:
            multiplier = 1.0

        bet_amount = base_bet * multiplier

        # Clamp to player's min/max range
        bet_amount = max(self.player_type.min_bet, min(bet_amount, self.player_type.max_bet))

        # Also clamp to available bankroll (can't bet more than you have)
        bet_amount = min(bet_amount, self.behavior_state.current_bankroll)

        return round(bet_amount, 2)


    def determine_outcome(self, bet_amount: float) -> tuple[bool, float]:

        """
        Determine if bet wins and calculate payout.

        Uses realistic house edge. Over time, player will lose ~5% of total wagered.

        Returns: (won: bool, payout: float)
        - If won=True, payout is the amount they receive (including original bet)
        - If won=False, payout is 0
        
        """

        # Win probability adjusted for house edge
        # For simplicity: 47.5% chance to win (giving house 5% edge)
        win_probability = 0.475

        won = random.random() < win_probability

        if won:
            # Simple 2x payout (bet $10, win $20 back including original bet)
            # This gives the right expected value with 47.5% win rate
            payout = bet_amount * 2
        else:
            payout = 0.0

        return won, round(payout, 2)


    def get_time_between_bets(self) -> float:
        """
        Get realistic delay between bets in seconds.

        Faster when tilting (frantic), slower when bored.
        """
        # Base delay depends on game type (slots are fast)
        base_delay = 5.0  # 5 seconds average for slots

        if self.behavior_state.emotional_state == EmotionalState.TILTING:
            # Frantic, rapid betting
            delay = random.uniform(2.0, 4.0)

        elif self.behavior_state.emotional_state == EmotionalState.BORED:
            # Slow, disengaged
            delay = random.uniform(8.0, 15.0)

        else:
            # Normal variance
            delay = random.uniform(3.0, 7.0)

        return delay


    def should_end_session(self) -> bool:
        """
        Determine if player should end their current session.

        Based on:
        - Bets completed vs typical session length
        - Bankroll state (bankrupt = forced end)
        - Emotional state (tilting might play longer, bored quits early)
        """
        # Bankrupt = must quit
        if self.behavior_state.current_bankroll <= 0:
            return True

        # Check if reached typical session length
        bets_done = self.behavior_state.bets_this_session
        typical_length = self.player_type.avg_bets_per_session

        # Emotional state affects session length
        if self.behavior_state.emotional_state == EmotionalState.TILTING:
            # Tilting players keep going (chasing)
            typical_length *= 1.5

        elif self.behavior_state.emotional_state == EmotionalState.BORED:
            # Bored players quit early
            typical_length *= 0.6

        elif self.behavior_state.emotional_state == EmotionalState.WINNING:
            # Winners play a bit longer (riding the streak)
            typical_length *= 1.2

        # Probabilistic end as we approach typical length
        if bets_done >= typical_length * 0.8:
            # Probability increases as we exceed typical length
            progress = bets_done / typical_length
            end_probability = min(0.95, (progress - 0.8) * 2.0)
            return random.random() < end_probability

        return False


def generate_bet_event(
    player_id: int,
    player_type: PlayerTypeProfile,
    behavior_state: PlayerBehaviorState,
    game_type: str = "slot",
) -> Optional[dict]:
    
    """
    Generate a single bet event.

    Returns None if player should end session, otherwise returns bet event dict.
    """

    generator = BetEventGenerator(player_type, behavior_state)

    # Check if session should end
    if generator.should_end_session():
        return None

    # Generate bet
    bet_amount = generator.generate_bet_amount()

    # Can't bet if no money
    if bet_amount <= 0:
        return None

    # Determine outcome
    won, payout = generator.determine_outcome(bet_amount)

    # Update behavior state
    behavior_state.record_bet_outcome(bet_amount, won, payout)

    # Check for state transitions
    behavior_state.check_tilt_transition(
        player_type.tilt_threshold,
        player_type.tilt_probability
    )
    behavior_state.check_boredom(player_type.boredom_threshold_sessions)

    # Create event
    event = {
        "player_id": player_id,
        "timestamp": datetime.utcnow().isoformat(),
        "game_type": game_type,
        "bet_amount": bet_amount,
        "won": won,
        "payout": payout,
        "net_result": payout - bet_amount if won else -bet_amount,

        # Behavioral context (for Monitor agent)
        "emotional_state": behavior_state.emotional_state.value,
        "consecutive_losses": behavior_state.consecutive_losses,
        "consecutive_wins": behavior_state.consecutive_wins,
        "current_bankroll": behavior_state.current_bankroll,
        "bets_this_session": behavior_state.bets_this_session,

        # Flags
        "is_at_risk": behavior_state.is_at_risk,
    }

    return event
