import random
from sqlalchemy import text

from .db import get_engine


def generate_player_preferences(player_id: int) -> dict:
    return {
        "player_id": player_id,
        "email_ok": random.choice([True, True, True, False]),
        "sms_ok": random.choice([True, True, False]),
        "push_ok": random.choice([True, True, True, True, False]),
        "language": random.choice(["en", "en", "en", "sl", "de"]),
        "do_not_disturb": False,
        "opted_out_marketing": False,
    }


def initialize_player_preferences(player_ids: list[int]):

    engine = get_engine()
    
    preferences = [generate_player_preferences(pid) for pid in player_ids]

    query = text("""
        INSERT INTO player_preferences (player_id, email_ok, sms_ok, push_ok, language, do_not_disturb, opted_out_marketing)
        VALUES (:player_id, :email_ok, :sms_ok, :push_ok, :language, :do_not_disturb, :opted_out_marketing)
        ON CONFLICT (player_id) DO NOTHING
    """)

    with engine.begin() as conn:
        conn.execute(query, preferences)

    print(f"Initialized preferences for {len(preferences)} players")
