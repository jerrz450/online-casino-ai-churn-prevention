import os
from sqlalchemy import create_engine

_engine = None

def get_engine():
    
    global _engine

    if _engine is None:

        POSTGRES_USER = os.environ.get('POSTGRES_CASINO_USER', 'casino_user')
        POSTGRES_PASSWORD = os.environ.get('POSTGRES_CASINO_PASSWORD', 'casino_pass')
        POSTGRES_DB = os.environ.get('POSTGRES_CASINO_DB', 'casino_churn')
        POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
        POSTGRES_PORT = os.environ.get('POSTGRES_PORT', '5432')
        DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

        _engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600
        )

    return _engine
