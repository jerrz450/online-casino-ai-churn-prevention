"""
Behavioral state models for player simulation.

Tracks player emotional state and how it evolves based on outcomes.
This drives realistic bet sizing, session length, and churn decisions.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import random


class EmotionalState(Enum):
    
    """Player's current emotional state."""

    NEUTRAL = "neutral"  # Normal play, following their type profile
    WINNING = "winning"  # On a streak, confident
    TILTING = "tilting"  # Frustrated, chasing losses
    BORED = "bored"  # Breaking even too long, losing interest
    RECOVERING = "recovering"  # Accepted intervention, giving it another shot


class ChurnReason(Enum):

    """Why a player stopped playing."""

    BANKRUPT = "bankrupt"  # Ran out of money
    BIG_LOSS = "big_loss"  # Lost too much, frustrated
    BIG_WIN = "big_win"  # Won big, cashing out
    BORED = "bored"  # Not excited anymore
    TILT_RAGE_QUIT = "tilt_rage_quit"  # Lost control, quit in anger
    NATURAL = "natural"  # Just done for now (might return)


@dataclass
class PlayerBehaviorState:

    """
    Tracks the current behavioral state of a player.

    This is the live state that evolves as they play. The Monitor agent
    watches these transitions to detect churn risk.
    """

    # Current state
    emotional_state: EmotionalState = EmotionalState.NEUTRAL

    # Streak tracking
    consecutive_wins: int = 0
    consecutive_losses: int = 0

    # Financial state
    current_bankroll: float = 0.0
    total_wagered: float = 0.0
    net_profit_loss: float = 0.0  # Negative = losing

    # Session tracking
    bets_this_session: int = 0
    session_start_bankroll: float = 0.0
    sessions_completed: int = 0
    sessions_since_last_big_event: int = 0  # Big win/loss

    # Churn indicators
    is_at_risk: bool = False  # Monitor agent sets this
    churn_risk_score: float = 0.0  # 0-1, Predictor agent sets this

    # Intervention tracking
    interventions_received: list = field(default_factory=list)
    last_intervention_accepted: Optional[str] = None

    # Flags
    has_churned: bool = False
    churn_reason: Optional[ChurnReason] = None


    def record_bet_outcome(self, bet_amount: float, won: bool, payout: float = 0.0):
        
        """
        Update state after a bet completes.

        This is where emotional state transitions happen based on outcomes.
        """

        self.bets_this_session += 1
        self.total_wagered += bet_amount

        if won:

            self.consecutive_wins += 1
            self.consecutive_losses = 0
            self.current_bankroll += payout
            self.net_profit_loss += (payout - bet_amount)

            # Transition to winning state after streak
            if self.consecutive_wins >= 3:
                self.emotional_state = EmotionalState.WINNING

        else:

            self.consecutive_losses += 1
            self.consecutive_wins = 0
            self.current_bankroll -= bet_amount
            self.net_profit_loss -= bet_amount


    def check_tilt_transition(self, tilt_threshold: int, tilt_probability: float) -> bool:
        
        """
        Check if player should transition to TILTING state.

        Returns True if player tilts, False if they just quit instead.
        """

        if self.consecutive_losses >= tilt_threshold:

            if random.random() < tilt_probability:
                self.emotional_state = EmotionalState.TILTING

                return True
            else:
                # Didn't tilt - they'll probably quit
                return False
            
        return False


    def check_boredom(self, boredom_threshold: int) -> bool:

        """Check if player is getting bored (breaking even too long)."""

        # Bored if sessions going nowhere (< 10% of starting bankroll variance)

        session_variance = abs(self.current_bankroll - self.session_start_bankroll)
        is_breaking_even = session_variance < (self.session_start_bankroll * 0.1)

        if is_breaking_even and self.sessions_since_last_big_event >= boredom_threshold:
            self.emotional_state = EmotionalState.BORED
            return True
        
        return False


    def calculate_session_result(self) -> dict:

        """Calculate session statistics."""

        session_profit = self.current_bankroll - self.session_start_bankroll
        session_roi = (session_profit / self.session_start_bankroll) * 100 if self.session_start_bankroll > 0 else 0

        return {
            "bets": self.bets_this_session,
            "profit_loss": session_profit,
            "roi_percent": session_roi,
            "ending_bankroll": self.current_bankroll,
        }


    def start_new_session(self):

        """Reset session-specific tracking."""

        self.sessions_completed += 1
        self.sessions_since_last_big_event += 1
        self.bets_this_session = 0
        self.session_start_bankroll = self.current_bankroll

        # Reset to neutral unless intervention is active
        if self.emotional_state != EmotionalState.RECOVERING:
            self.emotional_state = EmotionalState.NEUTRAL


    def apply_intervention_effect(self, intervention_type: str, amount: float):

        """

        Apply an intervention (bonus, free spins, etc.).

        This can change emotional state and bankroll, potentially preventing churn.

        """

        self.interventions_received.append({
            "type": intervention_type,
            "amount": amount,
            "at_session": self.sessions_completed,
        })

        # Boost bankroll (free money or free spins value)
        self.current_bankroll += amount

        # Transition to recovering state (gives them another chance)
        self.emotional_state = EmotionalState.RECOVERING
        self.last_intervention_accepted = intervention_type

        # Reset negative streaks
        self.consecutive_losses = 0
        self.sessions_since_last_big_event = 0


    def should_churn(
        self,
        base_churn_prob: float,
        big_loss_multiplier: float,
        big_win_multiplier: float,
    ) -> tuple[bool, Optional[ChurnReason]]:
        
        """
        Determine if player should churn based on current state.

        Returns (should_churn, reason)
        """

        # Bankrupt = automatic churn
        if self.current_bankroll <= 0:

            return True, ChurnReason.BANKRUPT

        # Tilt rage quit (high probability when tilting)
        if self.emotional_state == EmotionalState.TILTING:

            if random.random() < 0.3:  # 30% chance to rage quit when tilting
                return True, ChurnReason.TILT_RAGE_QUIT

        # Bored = likely to quit
        if self.emotional_state == EmotionalState.BORED:

            if random.random() < 0.5:  # 50% chance when bored
                return True, ChurnReason.BORED

        # Calculate dynamic churn probability based on financial state
        churn_prob = base_churn_prob

        # Big loss (lost >30% of starting bankroll)
        loss_percent = (self.net_profit_loss / self.current_bankroll) * -1 if self.current_bankroll > 0 else 0
        
        if loss_percent > 0.3:
            churn_prob *= big_loss_multiplier

            if random.random() < churn_prob:
                return True, ChurnReason.BIG_LOSS

        # Big win (won >50% of starting bankroll)
        win_percent = (self.net_profit_loss / self.session_start_bankroll) if self.session_start_bankroll > 0 else 0
        
        if win_percent > 0.5:
            churn_prob *= big_win_multiplier

            if random.random() < churn_prob:
                return True, ChurnReason.BIG_WIN

        # Natural churn (just done playing for now)
        if random.random() < base_churn_prob:
            return True, ChurnReason.NATURAL

        return False, None


    def mark_churned(self, reason: ChurnReason):

        """Mark player as churned."""
        
        self.has_churned = True
        self.churn_reason = reason
        self.is_at_risk = True  # Definitely at risk now!
        self.churn_risk_score = 1.0
