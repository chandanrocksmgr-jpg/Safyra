"""Document numbering: PREFIX{FY}{000001}, e.g. SAF26-27000001 or INV26-27000001.

Each prefix keeps its own counter per Indian financial year, so every series restarts at 000001 on 1 April.
"""

from pymongo import ReturnDocument

from lib.dates import now_in_app_tz
from lib.db import db

# Counter keys are pinned per prefix so a rename can never silently restart a live series.
COUNTER_KEYS = {"SAF": "order", "INV": "inv", "CN": "cn"}


def financial_year_label() -> str:
    """Indian financial year label for today in the shop's timezone: 1 Apr 2026 – 31 Mar 2027 is "26-27"."""
    today = now_in_app_tz()
    start_year = today.year if today.month >= 4 else today.year - 1
    return f"{start_year % 100:02d}-{(start_year + 1) % 100:02d}"


async def next_document_number(prefix: str) -> tuple[str, int]:
    """Next number in the prefix's financial-year series, e.g. ("INV26-27000001", 1)."""
    label = financial_year_label()
    key = f"{COUNTER_KEYS.get(prefix, prefix.lower())}-number-{label}"
    counter = await db.counters.find_one_and_update(
        {"id": key},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    sequence = int(counter["value"])
    return f"{prefix}{label}{sequence:06d}", sequence


async def next_order_number() -> str:
    """Order numbers are never reused: if a number somehow exists already, take the next one."""
    for _ in range(5):
        number, _sequence = await next_document_number("SAF")
        if not await db.order_requests.find_one({"request_number": number}, {"_id": 1}):
            return number
    return number
