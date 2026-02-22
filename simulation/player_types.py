from dataclasses import dataclass
from typing import Literal


@dataclass
class PlayerTypeProfile:

    type_name: Literal["whale", "grinder", "casual"]

    # Bet sizing (euros)
    min_bet:     float
    max_bet:     float
    typical_bet: float

    # Session behaviour
    avg_bets_per_session:    int
    session_frequency_per_day: float

    # Bankroll
    typical_bankroll: float

    # Tilt
    tilt_threshold:      int    # consecutive losses before tilting
    tilt_bet_multiplier: float  # how much bets increase when tilting
    tilt_probability:    float  # chance of tilting vs quitting

    # Churn
    base_churn_probability:        float
    churn_after_big_loss_multiplier: float
    churn_after_big_win_multiplier:  float
    boredom_threshold_sessions:     int

    # Interventions
    intervention_acceptance_rate: float
    prefers_free_spins:           bool

    # Business
    estimated_ltv_eur: float


WHALE = PlayerTypeProfile(

    type_name="whale",
    min_bet=50.0, max_bet=500.0,
    typical_bet=200.0,
    avg_bets_per_session=40,
    session_frequency_per_day=2.0,
    typical_bankroll=10000.0,
    tilt_threshold=8,
    tilt_bet_multiplier=1.5,
    tilt_probability=0.4,
    base_churn_probability=0.05,          # realistic: ~5% per session
    churn_after_big_loss_multiplier=2.0,
    churn_after_big_win_multiplier=0.5,
    boredom_threshold_sessions=20,
    intervention_acceptance_rate=0.7,
    prefers_free_spins=False,
    estimated_ltv_eur=5000.0,
)

GRINDER = PlayerTypeProfile(

    type_name="grinder",
    min_bet=5.0, max_bet=50.0,
    typical_bet=10.0,
    avg_bets_per_session=30,
    session_frequency_per_day=3.0,
    typical_bankroll=500.0,
    tilt_threshold=5,
    tilt_bet_multiplier=2.5,
    tilt_probability=0.7,
    base_churn_probability=0.08,          # realistic: ~8% per session
    churn_after_big_loss_multiplier=3.5,
    churn_after_big_win_multiplier=1.2,
    boredom_threshold_sessions=8,
    intervention_acceptance_rate=0.6,
    prefers_free_spins=True,
    estimated_ltv_eur=800.0,
)

CASUAL = PlayerTypeProfile(

    type_name="casual",
    min_bet=0.50,
    max_bet=10.0,
    typical_bet=2.0,
    avg_bets_per_session=20,
    session_frequency_per_day=0.5,
    typical_bankroll=100.0,
    tilt_threshold=3,
    tilt_bet_multiplier=2.0,
    tilt_probability=0.3,
    base_churn_probability=0.12,          # realistic: ~12% per session
    churn_after_big_loss_multiplier=4.0,
    churn_after_big_win_multiplier=2.0,
    boredom_threshold_sessions=3,
    intervention_acceptance_rate=0.4,
    prefers_free_spins=True,
    estimated_ltv_eur=150.0,
)

PLAYER_TYPES = {"whale": WHALE, "grinder": GRINDER, "casual": CASUAL}

def get_player_type(type_name: str) -> PlayerTypeProfile:

    return PLAYER_TYPES[type_name]
