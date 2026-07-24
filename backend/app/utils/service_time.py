from datetime import datetime
from zoneinfo import ZoneInfo


def get_uk_service_time() -> dict:
    now = datetime.now(ZoneInfo("Europe/London"))
    current_minutes = now.hour * 60 + now.minute
    start = 4 * 60 + 30
    end = 21 * 60 + 30
    return {
        "ukTime": now.strftime("%H:%M"),
        "available": start <= current_minutes <= end,
        "window": "04:30-21:30",
    }

