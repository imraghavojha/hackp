from __future__ import annotations

from typing import Any

SEED_TOOL = {
    "id": "tool_lead_formatter_v1",
    "name": "Lead List Formatter",
    "description": "Formats lead exports into manager-ready output.",
    "trigger": {
        "type": "on_url_visit",
        "url_pattern": "portal.example.com/leads",
        "prompt": "I built you a tool for this.",
    },
    "ui_prefs": {"theme": "dark", "density": "compact"},
}


def get_tools_for_url(url: str, user_id: str) -> dict[str, list[dict[str, Any]]]:
    matches = [SEED_TOOL] if "portal.example.com/leads" in url else []
    return {"tools": matches}


def get_tool_artifact(tool_id: str) -> str:
    return f"runtime/shell/tool_template.html#tool={tool_id}"


def post_tool_usage(tool_id: str, payload: dict[str, Any]) -> dict[str, bool]:
    return {"logged": bool(payload.get("user_id"))}
