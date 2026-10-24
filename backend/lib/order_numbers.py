"""Order numbering: SAF{FY}{000001}, e.g. SAF26-27000001. The counter restarts every 1 April."""

from pymongo import ReturnDocument

from lib.dates import now_in_app_tz
from lib.db import db


def financial_year_label() -> str:
    """Indian financial year label for today in the shop's timezone: 1 Apr 2026 – 31 Mar 2027 is "26-27"."""
    today = now_in_app_tz()
    start_year = today.year if today.month >= 4 else today.year - 1
    return f"{start_year % 100:02d}-{(start_year + 1) % 100:02d}"


async def next_order_number() -> str:
    label = financial_year_label()
    counter = await db.counters.find_one_and_update(
        {"id": f"order-number-{label}"},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"SAF{label}{int(counter['value']):06d}"
