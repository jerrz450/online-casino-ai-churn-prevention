import os
from redis.asyncio import Redis

_redis: Redis | None = None

async def get_redis() -> Redis:
    global _redis

    if _redis is None:
        _redis = Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0,
            decode_responses=True,
        )

    return _redis

async def close_redis():

    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None