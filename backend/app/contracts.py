from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


EventType = Literal["click", "input", "navigation", "copy", "paste", "submit", "select", "file_download"]
ToolStatus = Literal["generating", "ready", "needs_review", "disabled", "failed"]


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


class EventsBatchRequest(BaseModel):
    user_id: str
    events: list[EventModel]


class EventsBatchResponse(BaseModel):
    accepted: int
    buffered: int


class SourceEventWindow(BaseModel):
    start: str | None = None
    end: str | None = None
    repetition_count: int = 0


class TriggerTimeWindow(BaseModel):
    start: str
    end: str
    timezone: str


class ToolTrigger(BaseModel):
    type: Literal["on_url_visit"] = "on_url_visit"
    url_pattern: str
    prompt: str
    time_window: TriggerTimeWindow | None = None


class ArtifactInputSpec(BaseModel):
    primary_input: str
    accepts: list[str]
    sample_fixture_id: str | None = None


class ArtifactOutputSpec(BaseModel):
    format: str
    filename_pattern: str


class ProgrammaticInterface(BaseModel):
    input_type: str
    output_type: str


class ToolArtifact(BaseModel):
    type: str = "html_single_file"
    version: str = "1.0"
    artifact_id: str
    input_spec: ArtifactInputSpec
    output_spec: ArtifactOutputSpec
    primitives_used: list[str] = Field(default_factory=list)
    programmatic_interface: ProgrammaticInterface


class ToolStats(BaseModel):
    times_used: int = 0
    last_used: str | None = None
    avg_duration_ms: float | None = None


class ToolRecord(BaseModel):
    id: str
    user_id: str
    name: str
    description: str
    created_at: str
    source_event_window: SourceEventWindow
    trigger: ToolTrigger
    transformation_summary: list[str] = Field(default_factory=list)
    artifact: ToolArtifact
    ui_prefs: dict[str, Any] = Field(default_factory=dict)
    stats: ToolStats = Field(default_factory=ToolStats)
    status: ToolStatus = "ready"
    signature: str | None = None


class AnalysisWindow(BaseModel):
    start: str | None = None
    end: str | None = None


class AnalysisRecord(BaseModel):
    id: int
    user_id: str
    url: str
    signature: str | None = None
    transformation_name: str | None = None
    summary: str
    confidence: float | None = None
    repetition_count: int
    event_window: AnalysisWindow
    status: str
    tool_id: str | None = None
    created_at: str


class ToolsForUrlResponse(BaseModel):
    tools: list[ToolRecord]


class AnalysisForUrlResponse(BaseModel):
    analysis: AnalysisRecord | None


class ToolUsageRequest(BaseModel):
    user_id: str
    succeeded: bool
    duration_ms: int


class ToolUsageResponse(BaseModel):
    logged: bool


class FeedbackRequest(BaseModel):
    user_id: str
    tool_id: str
    feedback: str
    context: str


class FeedbackResponse(BaseModel):
    stored: bool
    memory_id: str


class InternalArtifactCreateRequest(BaseModel):
    user_id: str
    html_artifact: str


class InternalArtifactCreateResponse(BaseModel):
    artifact_id: str


class OrchestratorRunRequest(BaseModel):
    tool_id: str
    user_id: str
    input_data: Any
    config_override: dict[str, Any] | None = None


class OrchestratorRunResponse(BaseModel):
    run_id: str
    output_ref: str
    succeeded: bool
    artifact_id: str | None = None
    output_preview: Any | None = None
