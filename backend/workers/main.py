import asyncio
import platform

from backend.workers.consumer import run

if __name__ == "__main__":

    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(run())