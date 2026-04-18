from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


EventType = Literal["click", "input", "navigation", "copy", "paste", "submit", "select", "file_download"]


class Target(BaseModel):
    tag: str | None = None
    role: str | None = None
    text: str | None = None
    aria_label: str | None = None


class EventModel(BaseModel):
    session_id: str
    user_id: str
    timestamp: str
    url: str
    event_type: EventType
    target: Target
    value: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DetectionRequest(BaseModel):
    user_id: str
    events: list[EventModel]
    existing_tool_signatures: list[str] = Field(default_factory=list)


class EventWindow(BaseModel):
    start: str
    end: str


class DetectionResponse(BaseModel):
    detected: bool
    signature: str | None = None
    confidence: float | None = None
    transformation_name: str | None = None
    summary: str | None = None
    input_characterization: str | None = None
    output_characterization: str | None = None
    event_window: EventWindow | None = None
    repetition_count: int | None = None


class GenerateToolRequest(BaseModel):
    user_id: str
    detection: dict[str, Any]
    events: list[EventModel]
    user_prefs_hint: str = ""


class GenerateToolResponse(BaseModel):
    name: str
    description: str
    transformation_summary: list[str]
    html_artifact: str
    input_spec: dict[str, Any]
    output_spec: dict[str, Any]
    trigger: dict[str, Any]
    ui_prefs: dict[str, Any]
    primitives_used: list[str]
    programmatic_interface: dict[str, str]
