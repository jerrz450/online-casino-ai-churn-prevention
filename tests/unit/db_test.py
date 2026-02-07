from dotenv import load_dotenv
import os

load_dotenv(override= True)

print(f"POSTGRES_CASINO_USER: {os.getenv('POSTGRES_CASINO_USER')}")
print(f"POSTGRES_CASINO_PASSWORD: {os.getenv('POSTGRES_CASINO_PASSWORD')}")
print(f"POSTGRES_CASINO_DB: {os.getenv('POSTGRES_CASINO_DB')}")

from backend.db.postgres import get_db
from backend.db.connection import get_engine

db = get_db()

print("Testing database connection...")

engine = get_engine()
print(f"Engine created: {engine.url}")

print("\nTesting upsert_player...")
db.upsert_player(player_id=999, player_type="whale", ltv=50000.00)
print("Player 999 inserted")

print("\nTesting get_player_preferences...")
prefs = db.get_player_preferences(player_id=999)
print(f"Preferences: {prefs}")

print("\nSuccess!")