from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict

EventType = Literal["click", "input", "navigation", "copy", "paste", "submit", "select", "file_download"]


class Target(TypedDict):
    tag: str | None
    role: str | None
    text: str | None
    aria_label: str | None


class Event(TypedDict):
    session_id: str
    user_id: str
    timestamp: str
    url: str
    event_type: EventType
    target: Target
    value: str
    metadata: dict[str, Any]


class ToolTrigger(TypedDict):
    type: Literal["on_url_visit"]
    url_pattern: str
    prompt: str


class ToolRecord(TypedDict):
    id: str
    name: str
    description: str
    trigger: ToolTrigger
    ui_prefs: NotRequired[dict[str, Any]]
