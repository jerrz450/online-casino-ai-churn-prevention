"""Standalone DB helpers for the simulator (no backend dependency)."""

import os
from sqlalchemy import create_engine, text

def get_engine():
    url = (
        f"postgresql+psycopg2://"
        f"{os.getenv('POSTGRES_CASINO_USER')}:{os.getenv('POSTGRES_CASINO_PASSWORD')}"
        f"@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', 5432)}"
        f"/{os.getenv('POSTGRES_CASINO_DB')}"
    )
    return create_engine(url)


def upsert_players_batch(players: list):

    engine = get_engine()

    query = text("""
        INSERT INTO players (player_id, player_type, ltv, created_at, last_active)
        VALUES (:player_id, :player_type, :ltv, NOW(), NOW())
        ON CONFLICT (player_id) DO UPDATE
        SET player_type = EXCLUDED.player_type, ltv = EXCLUDED.ltv, last_active = NOW()
    """)

    with engine.begin() as conn:
        conn.execute(query, players)
