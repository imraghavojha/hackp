from __future__ import annotations

from datetime import datetime
from fnmatch import fnmatch
from zoneinfo import ZoneInfo

from backend.app.contracts import ToolTrigger


def matches_url(pattern: str, url: str) -> bool:
    wildcard = f"*{pattern}*"
    return fnmatch(url, wildcard)


def within_time_window(trigger: ToolTrigger, now: datetime | None = None) -> bool:
    if trigger.time_window is None:
        return True
    zone = ZoneInfo(trigger.time_window.timezone)
    current = now.astimezone(zone) if now is not None else datetime.now(tz=zone)
    current_minutes = current.hour * 60 + current.minute
    start_hour, start_minute = (int(part) for part in trigger.time_window.start.split(":", maxsplit=1))
    end_hour, end_minute = (int(part) for part in trigger.time_window.end.split(":", maxsplit=1))
    start_minutes = start_hour * 60 + start_minute
    end_minutes = end_hour * 60 + end_minute
    return start_minutes <= current_minutes <= end_minutes


def matches_tool_trigger(trigger: ToolTrigger, url: str, now: datetime | None = None) -> bool:
    return matches_url(trigger.url_pattern, url) and within_time_window(trigger, now=now)
