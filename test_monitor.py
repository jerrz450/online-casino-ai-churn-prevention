"""Test Monitor agent integration."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from simulation import PlayerSimulator

async def test():
    print("Testing Monitor Integration\n")
    sim = PlayerSimulator(num_players=15)
    sim.initialize_players()
    
    print("\nRunning 10 ticks...\n")
    for i in range(10):
        events = await sim.simulation_tick()
        if events:
            print(f"[Tick {i+1}] {len(events)} events")
        await asyncio.sleep(1)
    
    print("\nDone!")

if __name__ == "__main__":
    asyncio.run(test())
