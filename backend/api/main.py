import asyncio
import json  
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client: Redis | None = None

class ConnectionManager:

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):

        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


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

event_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)

async def event_processor():

    while True:

        event = await event_queue.get()

        try:
            await manager.broadcast(event)

        finally:
            event_queue.task_done()


@app.on_event("startup")
async def start_event_processor():
    
    global redis_client
    redis_client = Redis(host="redis", port=6379, db=0)
    await redis_client.ping()

@app.on_event("shutdown")
async def shutdown():
    
    global redis_client
    if redis_client is not None:
        await redis_client.close()

@app.post("/ingest/event")
async def ingest_event(event: dict):

    """
    High-throughput event ingestion endpoint.
    Publishes events to a Redis-backed queue for processing by worker services.
    """

    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis not initialized")
             
    try:
        payload = json.dumps(event)
        await redis_client.rpush("ingest:events", payload)

    except Exception:
        raise HTTPException(status_code=503, detail="Failed to enqueue event")
    
    return {"status": "accepted"}