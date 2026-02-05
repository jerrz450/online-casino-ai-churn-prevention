"""
Player simulation package.

Generates realistic casino player behavior for testing the AI agent system.
"""

from .player_types import PlayerTypeProfile, PLAYER_TYPES, get_player_type, WHALE, GRINDER, CASUAL
from .behavior_models import PlayerBehaviorState, EmotionalState, ChurnReason
from .event_generator import generate_bet_event, BetEventGenerator
from .player_simulator import PlayerSimulator, SimulatedPlayer, run_basic_simulation

__all__ = [
    
    # Player types
    "PlayerTypeProfile",
    "PLAYER_TYPES",
    "get_player_type",
    "WHALE",
    "GRINDER",
    "CASUAL",

    # Behavior models
    "PlayerBehaviorState",
    "EmotionalState",
    "ChurnReason",

    # Event generation
    "generate_bet_event",
    "BetEventGenerator",

    # Main simulator
    "PlayerSimulator",
    "SimulatedPlayer",
    "run_basic_simulation",
]
