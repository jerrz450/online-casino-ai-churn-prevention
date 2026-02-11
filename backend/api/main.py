from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):

        for connection in self.active_connections:

            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# Simulator control
simulator_task = None
simulator_instance = None
is_running = False

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    await manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/simulator/status")
async def get_simulator_status():
    return {"running": is_running}

@app.post("/simulator/start")
async def start_simulator(num_players: int = 50):
    global simulator_task, simulator_instance, is_running

    if is_running:
        return {"status": "already_running", "message": "Simulator is already running"}

    from ..simulation.player_simulator import PlayerSimulator
    from ..services.domain.event_broadcaster import get_broadcaster

    simulator_instance = PlayerSimulator(num_players=num_players)
    simulator_instance.initialize_players()

    broadcaster = get_broadcaster()
    broadcaster.set_manager(manager)

    # Send initial player list to frontend
    player_ids = list(simulator_instance.players.keys())
    await broadcaster.broadcast_initial_players(player_ids)

    async def run_sim():
        global is_running
        is_running = True
        await simulator_instance.run_simulation(tick_interval_seconds=0.5)
        is_running = False

    simulator_task = asyncio.create_task(run_sim())

    return {"status": "started", "num_players": num_players}

@app.post("/simulator/stop")
async def stop_simulator():
    global simulator_task, is_running, simulator_instance

    if not is_running:
        return {"status": "not_running", "message": "Simulator is not running"}

    if simulator_task:
        simulator_task.cancel()

        try:
            await simulator_task
            
        except asyncio.CancelledError:
            pass

    is_running = False
    simulator_instance = None

    return {"status": "stopped"}

def get_manager():
    return manager
