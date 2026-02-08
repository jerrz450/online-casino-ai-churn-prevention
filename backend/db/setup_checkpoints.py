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

def main():
    import asyncio
    import platform

    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(setup_checkpoints())

if __name__ == "__main__":
    main()
