from __future__ import annotations

from typing import Any


def post_events(payload: dict[str, Any]) -> dict[str, int]:
    events = payload.get("events", [])
    accepted = len(events)
    return {"accepted": accepted, "buffered": max(0, accepted - 500)}
