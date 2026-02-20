import asyncio
import time
from collections import deque
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Casino Simulation Server")

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

    async def connect(self, websocket: WebSocket) -> None:

        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:

        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:

        for connection in list(self.active_connections):

            try:
                await connection.send_json(message)
                
            except Exception:
                pass


class ForwardMetrics:

    def __init__(self):

        self.start_time = time.time()
        self.total_sent = 0
        self.total_success = 0
        self.total_errors = 0
        self.recent_latencies: deque = deque(maxlen=1000)

    def record(self, latency_ms: float, success: bool):
        
        self.total_sent += 1

        if success:
            self.total_success += 1

        else:
            self.total_errors += 1

        self.recent_latencies.append(latency_ms)

    def snapshot(self) -> dict:

        elapsed = time.time() - self.start_time
        latencies = list(self.recent_latencies)
        sorted_lat = sorted(latencies) if latencies else []
        
        return {
            "running_seconds": round(elapsed, 1),
            "total_sent": self.total_sent,
            "total_success": self.total_success,
            "total_errors": self.total_errors,
            "actual_rps": round(self.total_sent / elapsed, 2) if elapsed > 0 else 0.0,
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
            "p99_latency_ms": round(sorted_lat[int(len(sorted_lat) * 0.99)], 2) if sorted_lat else 0.0,
            "error_rate_pct": round(self.total_errors / self.total_sent * 100, 2) if self.total_sent else 0.0,
            "queue_depth": event_queue.qsize() if event_queue else 0,
        }


manager = ConnectionManager()
metrics: Optional[ForwardMetrics] = None
event_queue: Optional[asyncio.Queue] = None

simulator_task: Optional[asyncio.Task] = None
dispatcher_task: Optional[asyncio.Task] = None
simulator_instance = None
is_running = False

_target_url: Optional[str] = None
_requests_per_second: int = 10

async def event_dispatcher():
    
    """
    Reads all events from the queue, broadcasts to WebSocket clients,
    and optionally forwards to an HTTP endpoint at the configured RPS.
    """

    interval = 1.0 / _requests_per_second if _target_url else 0.0

    async with httpx.AsyncClient() as client:

        while is_running:

            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=1.0)

            except asyncio.TimeoutError:
                continue

            # Always push to WebSocket
            await manager.broadcast(event)

            # Forward to HTTP if configured
            if _target_url:

                t0 = time.perf_counter()

                try:
                    resp = await client.post(_target_url, json=event, timeout=5.0)
                    latency_ms = (time.perf_counter() - t0) * 1000
                    metrics.record(latency_ms, success=resp.status_code < 400)

                except Exception:
                    latency_ms = (time.perf_counter() - t0) * 1000
                    metrics.record(latency_ms, success=False)

                await asyncio.sleep(interval)


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


@app.get("/simulator/stats")
async def get_stats():

    if metrics is None:
        return {"error": "No load test running"}
    
    return metrics.snapshot()


@app.post("/simulator/start")
async def start_simulator(
    num_players: int = 50,
    tick_interval_seconds: float = 0.05,
    target_url: Optional[str] = None,
    requests_per_second: int = 10,
):
    global simulator_task, dispatcher_task, simulator_instance, is_running
    global metrics, event_queue, _target_url, _requests_per_second

    if is_running:
        return {"status": "already_running"}

    from simulation.player_simulator import PlayerSimulator

    _target_url = target_url
    _requests_per_second = requests_per_second

    event_queue = asyncio.Queue()
    metrics  = ForwardMetrics() if target_url else None

    simulator_instance = PlayerSimulator(
        num_players=num_players,
        event_queue=event_queue,
    )

    simulator_instance.initialize_players()

    # Broadcast initial player list to any connected WebSocket clients
    await manager.broadcast({
        "type":       "initial_players",
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "player_ids": list(simulator_instance.players.keys()),
    })

    async def run_sim():
        
        global is_running
        is_running = True

        await simulator_instance.run_simulation(tick_interval_seconds=tick_interval_seconds)

        is_running = False

    simulator_task  = asyncio.create_task(run_sim())
    dispatcher_task = asyncio.create_task(event_dispatcher())

    return {
        "status": "started",
        "num_players": num_players,
        "tick_interval_seconds": tick_interval_seconds,
        "target_url":  target_url,
        "requests_per_second":  requests_per_second if target_url else None,
    }


@app.post("/simulator/stop")
async def stop_simulator():

    global simulator_task, dispatcher_task, simulator_instance, is_running
    global metrics, event_queue

    if not is_running:
        return {"status": "not_running"}

    if simulator_instance is not None:
        simulator_instance.is_running = False

    for task in [simulator_task, dispatcher_task]:

        if task:
            task.cancel()

            try:
                await task
                
            except asyncio.CancelledError:
                pass

    final_stats = metrics.snapshot() if metrics else None

    is_running         = False
    simulator_instance = None
    simulator_task     = None
    dispatcher_task    = None
    metrics            = None
    event_queue        = None

    return {"status": "stopped", "final_stats": final_stats}