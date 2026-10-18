"""Server-side date helpers. The pod clock is UTC — anchor "today" here, never in the browser."""

import os
from datetime import datetime
from zoneinfo import ZoneInfo


def now_in_app_tz(tz: str | None = None) -> datetime:
    zone = tz or os.environ.get("APP_TZ", "Asia/Kolkata")
    return datetime.now(ZoneInfo(zone))


def today_iso(tz: str | None = None) -> str:
    """Today's date as YYYY-MM-DD in `tz` (default: APP_TZ env, else UTC)."""
    return now_in_app_tz(tz).strftime("%Y-%m-%d")
