import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.simulation.player_simulator import PlayerSimulator

async def test_end_session():
    sim = PlayerSimulator(num_players=1)
    sim.initialize_players()

    player = sim.players[1]

    await sim.start_player_session(player)
    await sim.end_player_session(player)
    from pprint import pprint
    pprint(player)

if __name__ == "__main__":
    asyncio.run(test_end_session())
