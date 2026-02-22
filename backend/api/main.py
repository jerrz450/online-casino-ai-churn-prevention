import asyncio
import json
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.agents.analyst_agent import get_analyst_agent
from backend.db.redis_client import get_redis, close_redis
from backend.db.redis_keys import RedisKeys

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = None

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
    redis_client = await get_redis()
    await redis_client.ping()

@app.on_event("shutdown")
async def shutdown():
    await close_redis()

@app.post("/ingest/new-run")
async def new_run():
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis not initialized")
    await redis_client.delete(RedisKeys.CURRENT_RUN_ID)
    return {"status": "ok"}


@app.post("/ingest/event")
async def ingest_event(event: dict):

    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis not initialized")
    
    try:
        await redis_client.rpush(RedisKeys.INGEST_EVENTS, json.dumps(event))

    except Exception:
        raise HTTPException(status_code=503, detail="Failed to enqueue event")
    
    return {"status": "accepted", "count": 1}


@app.post("/agents/analyze")
async def agents_analyze():
    thread_id = "analyst_main"
    return StreamingResponse(
        get_analyst_agent().stream_analysis(thread_id),
        media_type="text/event-stream",
        headers={"X-Thread-ID": thread_id},
    )


class ApplyRequest(BaseModel):
    approved_actions: list[str]
    params: dict = {}


@app.post("/agents/apply/{thread_id}")
async def agents_apply(thread_id: str, body: ApplyRequest):
    return StreamingResponse(
        get_analyst_agent().stream_apply(thread_id, body.approved_actions, body.params),
        media_type="text/event-stream",
    )


@app.post("/ingest/events")
async def ingest_events(events: List[dict]):

    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis not initialized")

    if not events:
        return {"status": "accepted", "count": 0}
    
    try:
        pipe = redis_client.pipeline()

        for event in events:
            pipe.rpush(RedisKeys.INGEST_EVENTS, json.dumps(event))
        await pipe.execute()

    except Exception:
        raise HTTPException(status_code=503, detail="Failed to enqueue events")
    
    return {"status": "accepted", "count": len(events)}