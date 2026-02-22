import asyncio
import json
import logging

from backend.db.redis_keys import RedisKeys

logger = logging.getLogger(__name__)

async def update_threshold(redis, value: float):

    await redis.set(RedisKeys.CHURN_THRESHOLD, str(value))
    logger.info(f"Churn threshold updated to {value}")

async def reload_model(redis):

    await redis.set(RedisKeys.MODEL_RELOAD, "1")
    logger.info("Model reload flag set")

async def update_train_config(redis, params: dict):
    await redis.set(RedisKeys.TRAIN_CONFIG, json.dumps(params))
    logger.info(f"Train config updated: {params}")


async def trigger_retrain():

    for module in ["backend.training.prepare", "backend.training.train"]:
        logger.info(f"Running {module}...")

        proc = await asyncio.create_subprocess_exec(
            "python", "-m", module,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        stdout, _ = await proc.communicate()

        if stdout:
            logger.info(stdout.decode())

        if proc.returncode != 0:
            raise RuntimeError(f"{module} exited with code {proc.returncode}")
        
    logger.info("Retrain complete")
