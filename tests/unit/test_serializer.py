"""Test serializer integration with simulator."""

import asyncio
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.simulation import PlayerSimulator


async def test_serializer_integration():
    print("Testing PlayerContextSerializer integration...\n")

    simulator = PlayerSimulator(num_players=10)
    simulator.initialize_players()

    # Run for a few ticks to generate some activity
    print("\nRunning simulation for 10 seconds...\n")
    
    for _ in range(5):
        events = await simulator.simulation_tick()
        if events:
            # Show first event with monitor context
            event = events[0]
            print(f"Player {event['player_id']} bet €{event['bet_amount']}")
            print(f"Monitor context keys: {list(event.get('monitor_context', {}).keys())}")
            print(f"Emotional state: {event['monitor_context']['emotional_state']}")
            print(f"Consecutive losses: {event['monitor_context']['consecutive_losses']}\n")
        await asyncio.sleep(2)

    # Test context retrieval methods
    print("\n" + "="*60)
    print("Testing context retrieval methods...")
    print("="*60)

    # Get a player
    player = list(simulator.players.values())[0]
    player_id = player.player_id

    # Test different context types
    print(f"\n1. Monitor context for Player {player_id}:")
    monitor_ctx = simulator.get_player_context(player_id, "monitor")
    print(json.dumps(monitor_ctx, indent=2))

    print(f"\n2. Predictor context for Player {player_id}:")
    predictor_ctx = simulator.get_player_context(player_id, "predictor")
    print(json.dumps(predictor_ctx, indent=2))

    print(f"\n3. Designer context for Player {player_id}:")
    designer_ctx = simulator.get_player_context(player_id, "designer")
    print(json.dumps(designer_ctx, indent=2))

    print("\n[OK] Serializer integration working!")


if __name__ == "__main__":
    asyncio.run(test_serializer_integration())
