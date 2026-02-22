from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import random

class EmotionalState(Enum):

    NEUTRAL    = "neutral"
    WINNING    = "winning"
    TILTING    = "tilting"
    BORED      = "bored"
    RECOVERING = "recovering"


class ChurnReason(Enum):

    BANKRUPT      = "bankrupt"
    BIG_LOSS      = "big_loss"
    BIG_WIN       = "big_win"
    BORED         = "bored"
    TILT_RAGE_QUIT = "tilt_rage_quit"
    NATURAL       = "natural"

@dataclass
class PlayerBehaviorState:

    emotional_state: EmotionalState = EmotionalState.NEUTRAL

    consecutive_wins: int = 0
    consecutive_losses: int = 0

    current_bankroll: float = 0.0
    session_start_bankroll: float = 0.0
    total_wagered: float = 0.0
    net_profit_loss: float = 0.0

    bets_this_session: int = 0
    sessions_completed: int = 0
    sessions_since_last_big_event: int = 0

    is_at_risk: bool  = False
    churn_risk_score: float = 0.0

    interventions_received : list = field(default_factory=list)
    last_intervention_accepted : Optional[str] = None
    bets_since_intervention : int = 0

    has_churned:  bool = False
    churn_reason: Optional[ChurnReason] = None

    # Reduced by successful interventions — floors at 0.3 (intervention can't eliminate churn)
    effective_churn_modifier: float = 1.0


    def record_bet_outcome(self, bet_amount: float, won: bool, payout: float,
                           tilt_threshold: int, tilt_probability: float):
        self.bets_this_session += 1
        self.total_wagered     += bet_amount

        if won:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            self.current_bankroll += payout
            self.net_profit_loss += payout - bet_amount

        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
            self.current_bankroll -= bet_amount
            self.net_profit_loss -= bet_amount

        self._update_emotional_state(tilt_threshold, tilt_probability)


    def _update_emotional_state(self, tilt_threshold: int, tilt_probability: float):
        
        # Recovering players need a few bets to stabilise before changing state

        if self.emotional_state == EmotionalState.RECOVERING:

            self.bets_since_intervention += 1

            if self.bets_since_intervention < 5:
                return
            self.emotional_state = EmotionalState.NEUTRAL

        if self.consecutive_losses >= tilt_threshold:

            if random.random() < tilt_probability:
                self.emotional_state = EmotionalState.TILTING
                self.is_at_risk = True
                self.sessions_since_last_big_event = 0

        elif self.consecutive_wins >= 3:

            self.emotional_state = EmotionalState.WINNING
            self.sessions_since_last_big_event = 0

        elif self.emotional_state == EmotionalState.WINNING and self.consecutive_wins == 0:

            self.emotional_state = EmotionalState.NEUTRAL


    def check_boredom(self, boredom_threshold: int):

        """Call at session end. Boredom builds when nothing interesting happens."""

        if self.emotional_state in (EmotionalState.TILTING, EmotionalState.WINNING):
            return

        breaking_even = abs(self.current_bankroll - self.session_start_bankroll) < self.session_start_bankroll * 0.1

        if breaking_even and self.sessions_since_last_big_event >= boredom_threshold:
            self.emotional_state = EmotionalState.BORED


    def should_churn(self, base_churn_prob: float, big_loss_multiplier: float,
                     big_win_multiplier: float) -> tuple[bool, Optional[ChurnReason]]:
        
        if self.current_bankroll <= 0:
            return True, ChurnReason.BANKRUPT

        if self.emotional_state == EmotionalState.TILTING and random.random() < 0.3:
            return True, ChurnReason.TILT_RAGE_QUIT

        if self.emotional_state == EmotionalState.BORED and random.random() < 0.5:
            return True, ChurnReason.BORED

        start = self.session_start_bankroll or 1.0
        loss_pct = (self.session_start_bankroll - self.current_bankroll) / start
        win_pct  = (self.current_bankroll - self.session_start_bankroll)  / start

        effective = base_churn_prob * self.effective_churn_modifier

        if loss_pct > 0.3 and random.random() < effective * big_loss_multiplier:
            return True, ChurnReason.BIG_LOSS

        if win_pct > 0.5 and random.random() < effective * big_win_multiplier:
            return True, ChurnReason.BIG_WIN

        if random.random() < effective:
            return True, ChurnReason.NATURAL

        return False, None


    def start_new_session(self):

        self.sessions_completed += 1
        self.sessions_since_last_big_event += 1
        self.bets_this_session = 0
        self.session_start_bankroll = self.current_bankroll

        if self.emotional_state != EmotionalState.RECOVERING:
            self.emotional_state = EmotionalState.NEUTRAL


    def apply_intervention(self, intervention_type: str, amount: float):
        
        self.interventions_received.append({
            "type": intervention_type, "amount": amount,
            "at_session": self.sessions_completed,
        })

        self.current_bankroll += amount
        self.emotional_state = EmotionalState.RECOVERING
        self.last_intervention_accepted = intervention_type
        self.bets_since_intervention = 0
        self.consecutive_losses = 0
        self.sessions_since_last_big_event = 0
        self.effective_churn_modifier = max(0.3, self.effective_churn_modifier - 0.2)


    def mark_churned(self, reason: ChurnReason):

        self.has_churned = True
        self.churn_reason = reason
        self.is_at_risk = True
        self.churn_risk_score = 1.0
