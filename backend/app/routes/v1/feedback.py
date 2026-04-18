from __future__ import annotations

from typing import Any


def post_feedback(payload: dict[str, Any]) -> dict[str, Any]:
    tool_id = payload.get("tool_id", "unknown")
    return {"stored": True, "memory_id": f"mem_{tool_id}"}
