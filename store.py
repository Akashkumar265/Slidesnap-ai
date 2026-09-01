import os
from datetime import date

# V1-only in-memory daily usage store.
# Restarting the bot resets the counters. Replace with PostgreSQL/Redis in production.
_usage = {}

def can_generate(user_id: int) -> bool:
    limit = int(os.getenv("FREE_GENERATIONS_PER_DAY", "3"))
    key = (user_id, date.today().isoformat())
    return _usage.get(key, 0) < limit

def record_generation(user_id: int):
    key = (user_id, date.today().isoformat())
    _usage[key] = _usage.get(key, 0) + 1
