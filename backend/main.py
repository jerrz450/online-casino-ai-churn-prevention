import asyncio
import platform
import uvicorn
from .api.main import app

if __name__ == "__main__":

    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Just start the API server, simulator controlled via /simulator/start endpoint
    uvicorn.run(app, host="0.0.0.0", port=8000)
