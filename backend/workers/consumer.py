"""
Redis event consumer.

Reads events from ingest:events and batch-inserts into
raw_training_events (Postgres) for the training pipeline.
"""

import asyncio
import json
import uuid
from uuid import UUID

from sqlalchemy import text

from backend.db.connection import get_engine
from backend.db.redis_client import get_redis
from backend.db.redis_keys import RedisKeys

BATCH_SIZE = 50  # flush after this many events
BATCH_TIMEOUT = 0.5  # or after this many seconds, whichever comes first

async def _get_or_create_run_id(redis) -> UUID:
    
    """
    Returns the current simulation run_id from Redis.
    If the simulator hasn't set one, generates a fallback UUID.

    """

    run_id_str = await redis.get(RedisKeys.CURRENT_RUN_ID)
    
    if run_id_str:
        return UUID(run_id_str)
    
    fallback = uuid.uuid4()
    
    await redis.set(RedisKeys.CURRENT_RUN_ID, str(fallback))
    
    print(f"[Consumer] No active run_id in Redis — generated fallback {fallback}")
    return fallback

engine = get_engine()

def _insert_batch(run_id: UUID, batch: list[dict]):

    """Synchronous batch insert into raw_training_events (run in thread pool)."""

    rows = [
        {
            "run_id":     str(run_id),
            "player_id":  event.get("player_id"),
            "event_type": event.get("type", "bet_event"),
            "payload":    json.dumps(event),
        }
        for event in batch
    ]

    with engine.begin() as conn:

        conn.execute(
            text("""
                INSERT INTO raw_training_events (run_id, player_id, event_type, payload)
                VALUES (:run_id, :player_id, :event_type, :payload)
            """),
            rows,
        )

async def _forward_to_decisions_queue(redis, batch: list[dict]) -> int:
  
    bet_events = [e for e in batch if e.get("type") == "bet_event"]
   
    if not bet_events:
        print(f"[Consumer] No bet_events in batch of {len(batch)}")
        return 0
    
    pipe = redis.pipeline()
    
    for event in bet_events:
        pipe.rpush(RedisKeys.DECISIONS_QUEUE, json.dumps(event))

    await pipe.execute()

    return len(bet_events)


async def _flush(redis, run_id: UUID, batch: list[dict]):

    # Run _insert_batch and _forward_to_decisions concurrently, waiting for both to complete before proceeding. -> In the same thread.
    _, forwarded = await asyncio.gather(asyncio.to_thread(
        _insert_batch, run_id, batch),
        _forward_to_decisions_queue(redis, batch),
    )

    print(f"[Consumer] Flushed {len(batch)} → DB, {forwarded} → decisions:queue (run={run_id})")


async def run():

    redis  = await get_redis()
    run_id = await _get_or_create_run_id(redis)

    print(f"[Consumer] Listening on {RedisKeys.INGEST_EVENTS} (run={run_id})")

    batch = []
    last_flush = asyncio.get_running_loop().time()

    while True:

        # Blocking pop with a short timeout so we can check the batch timer
        # wait → wake instantly when message arrives
        result = await redis.blpop(RedisKeys.INGEST_EVENTS, timeout= BATCH_TIMEOUT)

        if result:
            _, raw = result
            batch.append(json.loads(raw))

        now  = asyncio.get_running_loop().time()

        # this checks if enough time has passed since the last flush, even if the batch size hasn't been reached.
        # This ensures that we clean up any remaining events in the batch in a timely manner, preventing excessive delays in processing.
        time_elapsed = now - last_flush >= BATCH_TIMEOUT

        if batch and (len(batch) >= BATCH_SIZE or time_elapsed):

            # Refresh run_id on each flush in case simulator started a new run
            run_id = await _get_or_create_run_id(redis)

            # Flush batch to DB and decisions queue concurrently, then reset batch and timer
            await _flush(redis, run_id, batch)

            batch = []
            last_flush = now
