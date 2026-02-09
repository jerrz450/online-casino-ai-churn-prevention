import asyncio
import platform
import uvicorn
from .api.main import app, get_manager
from .simulation.player_simulator import PlayerSimulator

async def run_simulation(num_players):

    simulator = PlayerSimulator(num_players=num_players)
    simulator.initialize_players()

    from .services.domain.event_broadcaster import get_broadcaster

    broadcaster = get_broadcaster()
    broadcaster.set_manager(get_manager())

    await simulator.run_simulation(tick_interval_seconds=2.0)

def start_api():

    config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
    server = uvicorn.Server(config)
    return server

async def main(num_players = 20):

    api_server = start_api()

    await asyncio.gather(
        api_server.serve(),
        run_simulation(num_players)
    )

if __name__ == "__main__":

    import sys

    if len(sys.argv) > 1:
        num_players = int(sys.argv[1])
    else:
        num_players = 50
    
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main(num_players))
