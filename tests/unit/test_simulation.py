"""
Quick test of the player simulation system.

Run this to verify the simulation generates realistic player behavior.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.simulation import PlayerSimulator


async def test_simulation():
    """Run a short simulation test."""

    print("=" * 70)
    print("CASINO PLAYER SIMULATION TEST")
    print("=" * 70)

    # Create simulator with just 20 players for quick test
    simulator = PlayerSimulator(num_players=20)

    # Initialize players
    simulator.initialize_players()

    # Show initial player types
    print("\nPlayer Population:")
    for player_id, player in list(simulator.players.items())[:5]:  # Show first 5
        print(f"  Player {player_id}: {player.player_type.type_name.upper()}, "
              f"€{player.behavior_state.current_bankroll:.2f} bankroll")
    print(f"  ... and {len(simulator.players) - 5} more players\n")

    # Run simulation for 30 seconds
    print("Running simulation for 30 seconds...\n")

    # Run in background with timeout
    try:
        await asyncio.wait_for(
            simulator.run_simulation(tick_interval_seconds=3.0),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        simulator.is_running = False
        print("\n[OK] Test completed")

    # Final stats
    print("\n" + "=" * 70)
    simulator.print_stats()
    print("=" * 70)

    # Show some player details
    print("\nSample Player Details:")
    for player in list(simulator.players.values())[:3]:
        state = player.behavior_state
        print(f"\n  Player {player.player_id} ({player.player_type.type_name.upper()}):")
        print(f"    Bankroll: €{state.current_bankroll:.2f} (started with €{player.player_type.typical_bankroll:.2f})")
        print(f"    P/L: €{state.net_profit_loss:.2f}")
        print(f"    Sessions: {state.sessions_completed}")
        print(f"    Total wagered: €{state.total_wagered:.2f}")
        print(f"    Emotional state: {state.emotional_state.value}")
        print(f"    Churned: {state.has_churned}")


if __name__ == "__main__":
    asyncio.run(test_simulation())
