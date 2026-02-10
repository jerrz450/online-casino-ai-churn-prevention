"""
Player archetypes with distinct behavioral profiles.

Player types:
    Whale - Big fish, longer sessions, larger bankroll.
    Grinder - Medium bets, more consistent, frequent play, controlled bankroll, moderate churn risk.
    Casual - Casual gambler, small bankroll, plays for entertaiment, high churn risk.

Each type has different:
- Bet sizing patterns
- Session duration preferences
- Tilt thresholds (when they start betting irrationally)
- Churn triggers (what makes them quit)
- Response to interventions

"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class PlayerTypeProfile:
    
    """Behavioral profile for a player archetype."""

    # Identity
    type_name: Literal["whale", "grinder", "casual"]

    # Bet sizing (in euros)
    min_bet: float
    max_bet: float
    typical_bet: float  # Most common bet size

    # Session patterns
    avg_session_duration_minutes: float
    avg_bets_per_session: int
    session_frequency_per_day: float  # How often they play

    # Bankroll management
    typical_bankroll: float  # Starting funds

    # Tilt behavior (when they start betting irrationally after losses)
    tilt_threshold: int  # Consecutive losses before tilting
    tilt_bet_multiplier: float  # How much they increase bets when tilting (2.0 = double)
    tilt_probability: float  # 0-1, how likely to tilt vs just quit

    # Churn risk factors
    base_churn_probability: float  # 0-1, daily churn chance when neutral
    churn_after_big_loss_multiplier: float  # How much more likely after losing streak
    churn_after_big_win_multiplier: float  # Some quit after big win (take money and run)
    boredom_threshold_sessions: int  # Sessions before getting bored if breaking even

    # Intervention response (how likely to accept offers)
    intervention_acceptance_rate: float  # 0-1
    prefers_free_spins: bool  # vs bonus cash

    # Lifetime value (business metrics)
    estimated_ltv_eur: float  # Average total spend over lifetime


""" The three main player archetypes """

WHALE = PlayerTypeProfile(

    type_name="whale",

    # High roller - big bets
    min_bet=50.0,
    max_bet=500.0,
    typical_bet=200.0,

    # Long, frequent sessions
    avg_session_duration_minutes=45.0,
    avg_bets_per_session=40,
    session_frequency_per_day=2.0,

    # Large bankroll
    typical_bankroll=10000.0,

    # Harder to tilt, but when they do it's dangerous
    tilt_threshold=8,  # Takes more losses to tilt
    tilt_bet_multiplier=1.5,  # More measured even when tilting
    tilt_probability=0.4,  # Often just takes a break instead

    # Lower churn risk overall (sticky customers)
    base_churn_probability=0.25,  # 25% session-end churn when neutral
    churn_after_big_loss_multiplier=2.0,
    churn_after_big_win_multiplier=0.5,  # Winning keeps them playing
    boredom_threshold_sessions=20,  # Takes a while to get bored

    # Responsive to premium interventions
    intervention_acceptance_rate=0.7,
    prefers_free_spins=False,  # Likes bonus cash for flexibility

    # High value
    estimated_ltv_eur=5000.0,
)


GRINDER = PlayerTypeProfile(

    type_name="grinder",

    # Medium bets, consistent
    min_bet=5.0,
    max_bet=50.0,
    typical_bet=10.0,

    # Moderate sessions, very frequent play
    avg_session_duration_minutes=30.0,
    avg_bets_per_session=30,
    session_frequency_per_day=3.0,  # Plays multiple times daily

    # Controlled bankroll
    typical_bankroll=500.0,

    # Tilts more easily (chasing losses)
    tilt_threshold=5,
    tilt_bet_multiplier=2.5,  # Aggressive when tilting
    tilt_probability=0.7,  # Usually tilts rather than quitting

    # Moderate churn risk
    base_churn_probability=0.35,  # 35% session-end churn
    churn_after_big_loss_multiplier=3.5,  # Very sensitive to losses
    churn_after_big_win_multiplier=1.2,  # Slight increase (might cash out)
    boredom_threshold_sessions=8,

    # Moderately responsive to offers
    intervention_acceptance_rate=0.6,
    prefers_free_spins=True,  # Extends playtime without risk

    # Medium value
    estimated_ltv_eur=800.0,
)


CASUAL = PlayerTypeProfile(

    type_name="casual",

    # Small bets, entertainment gambling
    min_bet=0.50,
    max_bet=10.0,
    typical_bet=2.0,

    # Short, infrequent sessions
    avg_session_duration_minutes=15.0,
    avg_bets_per_session=20,
    session_frequency_per_day=0.5,  # Every couple days

    # Small bankroll
    typical_bankroll=100.0,

    # Tilts rarely (quits when frustrated)
    tilt_threshold=3,  # Low tolerance
    tilt_bet_multiplier=2.0,
    tilt_probability=0.3,  # Usually just quits

    # High churn risk (not deeply engaged)
    base_churn_probability=0.50,  # 50% session-end churn
    churn_after_big_loss_multiplier=4.0,  # Very sensitive
    churn_after_big_win_multiplier=2.0,  # Might quit satisfied
    boredom_threshold_sessions=3,  # Gets bored quickly

    # Less responsive (not checking app often)
    intervention_acceptance_rate=0.4,
    prefers_free_spins=True,  # Low risk, fun

    # Low value but lots of them
    estimated_ltv_eur=150.0,
)


# Registry for easy access
PLAYER_TYPES = {
    "whale": WHALE,
    "grinder": GRINDER,
    "casual": CASUAL,
}


def get_player_type(type_name: str) -> PlayerTypeProfile:

    """Get player type profile by name."""

    return PLAYER_TYPES[type_name]
