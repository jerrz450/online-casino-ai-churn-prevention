import random
from datetime import datetime

from .player_types import PlayerTypeProfile
from .behavior_models import PlayerBehaviorState, EmotionalState


HOUSE_EDGE = 0.05  # 95% RTP


def get_bet_amount(player_type: PlayerTypeProfile, state: PlayerBehaviorState) -> float:

    multipliers = {
        EmotionalState.NEUTRAL:    lambda: random.uniform(0.7, 1.3),
        EmotionalState.WINNING:    lambda: random.uniform(1.0, 1.4),
        EmotionalState.TILTING:    lambda: player_type.tilt_bet_multiplier * random.uniform(0.9, 1.5),
        EmotionalState.BORED:      lambda: random.uniform(0.5, 0.9),
        EmotionalState.RECOVERING: lambda: random.uniform(0.8, 1.2),
    }

    multiplier = multipliers.get(state.emotional_state, lambda: 1.0)()
    amount = player_type.typical_bet * multiplier
    amount = max(player_type.min_bet, min(amount, player_type.max_bet))
    return round(min(amount, state.current_bankroll), 2)


def get_time_between_bets(state: PlayerBehaviorState) -> float:
    if state.emotional_state == EmotionalState.TILTING:
        return random.uniform(0.1, 0.3)
    
    if state.emotional_state == EmotionalState.BORED:

        return random.uniform(0.5, 1.0)
    
    return random.uniform(0.2, 0.6)


def generate_bet_event(player_id: int, player_type: PlayerTypeProfile,
                       state: PlayerBehaviorState) -> dict:
    bet_amount = get_bet_amount(player_type, state)

    if bet_amount <= 0:
        return None

    won  = random.random() < 0.475
    payout = round(bet_amount * 2, 2) if won else 0.0

    state.record_bet_outcome(
        bet_amount, won, payout,
        tilt_threshold=player_type.tilt_threshold,
        tilt_probability=player_type.tilt_probability,
    )

    return {
        "player_id":         player_id,
        "timestamp":         datetime.utcnow().isoformat(),
        "game_type":         "slot",
        "bet_amount":        bet_amount,
        "won":               won,
        "payout":            payout,
        "net_result":        round(payout - bet_amount if won else -bet_amount, 2),
        "emotional_state":   state.emotional_state.value,
        "consecutive_losses": state.consecutive_losses,
        "consecutive_wins":  state.consecutive_wins,
        "current_bankroll":  state.current_bankroll,
        "bets_this_session": state.bets_this_session,
        "is_at_risk":        state.is_at_risk,
    }
