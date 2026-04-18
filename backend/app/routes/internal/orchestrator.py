from __future__ import annotations

from typing import Any


def run_tool(payload: dict[str, Any]) -> dict[str, Any]:
    tool_id = payload.get("tool_id", "tool_stub")
    return {"run_id": f"run_{tool_id}", "output_ref": "inline", "succeeded": True}
