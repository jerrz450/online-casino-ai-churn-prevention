from backend.db.connection import get_engine
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from dotenv import load_dotenv

load_dotenv(override=True)

async def setup_checkpoints():

    engine = get_engine()

    conn_string = f"postgresql://{engine.url.username}:{engine.url.password}@{engine.url.host}:{engine.url.port}/{engine.url.database}"

    async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
        await checkpointer.setup()

    print("Checkpoint tables created successfully")

async def connect_to_checkpoints():

    from psycopg import AsyncConnection

    engine = get_engine()

    conn_string = f"postgresql://{engine.url.username}:{engine.url.password}@{engine.url.host}:{engine.url.port}/{engine.url.database}"

    conn = await AsyncConnection.connect(conn_string, autocommit=True, prepare_threshold=0)
    return AsyncPostgresSaver(conn)

async def get_recent_messages_checkpoint(checkpointer, thread_id: str, limit: int = 10):

    config = {"configurable": {"thread_id": thread_id}}

    try:
        checkpoint_tuple = await checkpointer.aget_tuple(config)

        if not checkpoint_tuple:
            return []

        checkpoint = checkpoint_tuple.checkpoint

        if "channel_values" in checkpoint and "messages" in checkpoint["channel_values"]:
            messages = checkpoint["channel_values"]["messages"]

        elif "messages" in checkpoint:
            messages = checkpoint["messages"]

        else:
            return []

        return messages[-limit:] if messages else []

    except Exception as e:
        print(f"Failed to retrieve checkpoint memory: {e}")
        return []

def main():
    
    import asyncio
    import platform

    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(setup_checkpoints())

if __name__ == "__main__":
    main()
