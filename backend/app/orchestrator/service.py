from __future__ import annotations

from typing import Any


def run_tool(tool_id: str, user_id: str, input_data: Any, config_override: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "run_id": f"run_{tool_id}",
        "user_id": user_id,
        "output_ref": "inline",
        "succeeded": True,
        "config_override": config_override or {},
    }
