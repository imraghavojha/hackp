from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.app.artifacts.store import ArtifactStore
from backend.app.artifacts.validator import validate_html_artifact
from backend.app.contracts import (
    ArtifactInputSpec,
    ArtifactOutputSpec,
    ProgrammaticInterface,
    SourceEventWindow,
    ToolArtifact,
    ToolRecord,
    ToolStats,
    ToolTrigger,
)
from backend.app.store.repository import PlatformRepository


DETECTION_INTERVAL_SECONDS = 120
MIN_EVENTS_FOR_DETECTION = 50
MIN_ACTIVITY_WINDOW_SECONDS = 600
MIN_REPETITIONS_TO_SUGGEST = 3


def utc_now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_timestamp(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


class AiGateway(Protocol):
    def detect_transformation(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def generate_tool(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class AiGatewayError(RuntimeError):
    pass


class HttpAiGateway:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def detect_transformation(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/ai/detect_transformation", payload)

    def generate_tool(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/ai/generate_tool", payload)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise AiGatewayError(str(exc)) from exc


class DetectionScheduler:
    def __init__(self, repository: PlatformRepository, artifact_store: ArtifactStore, ai_gateway: AiGateway):
        self.repository = repository
        self.artifact_store = artifact_store
        self.ai_gateway = ai_gateway

    def maybe_process_user(self, user_id: str) -> ToolRecord | None:
        pending_events = self.repository.get_pending_events(user_id)
        if not pending_events or not self._threshold_reached(pending_events):
            return None
        last_event_id = pending_events[-1]["id"]

        try:
            detection = self.ai_gateway.detect_transformation(
                {
                    "user_id": user_id,
                    "events": [self._strip_event_identifier(event) for event in pending_events],
                    "existing_tool_signatures": self.repository.list_tool_signatures(user_id),
                }
            )
        except AiGatewayError:
            self.repository.mark_events_processed(user_id=user_id, last_event_id=last_event_id, detected_at=utc_now())
            return None

        if not detection.get("detected"):
            self.repository.mark_events_processed(user_id=user_id, last_event_id=last_event_id, detected_at=utc_now())
            return None
        if int(detection.get("repetition_count") or 0) < MIN_REPETITIONS_TO_SUGGEST:
            self.repository.mark_events_processed(user_id=user_id, last_event_id=last_event_id, detected_at=utc_now())
            return None

        generated = self._generate_valid_artifact(
            user_id=user_id,
            detection=detection,
            pending_events=pending_events,
        )
        if generated is None:
            self.repository.mark_events_processed(user_id=user_id, last_event_id=last_event_id, detected_at=utc_now())
            return None

        tool_id = f"tool_{detection['signature'].removeprefix('sig_')}_v1"
        artifact_id, artifact_path = self.artifact_store.create_artifact(
            generated["html_artifact"],
            preferred_id=f"art_{tool_id}",
        )
        self.repository.store_artifact_record(artifact_id=artifact_id, user_id=user_id, html_path=artifact_path)
        tool = self._build_tool_record(
            user_id=user_id,
            tool_id=tool_id,
            detection=detection,
            generated=generated,
            artifact_id=artifact_id,
        )
        self.repository.save_tool(tool)
        self.repository.mark_events_processed(user_id=user_id, last_event_id=last_event_id, detected_at=utc_now())
        return tool

    def _generate_valid_artifact(
        self,
        *,
        user_id: str,
        detection: dict[str, Any],
        pending_events: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        payload = {
            "user_id": user_id,
            "detection": detection,
            "events": [self._strip_event_identifier(event) for event in pending_events],
            "user_prefs_hint": "\n".join(self.repository.recent_feedback(user_id)),
        }
        for _attempt in range(2):
            try:
                generated = self.ai_gateway.generate_tool(payload)
            except AiGatewayError:
                return None
            validation = validate_html_artifact(generated["html_artifact"])
            if validation.is_valid:
                return generated
        return None

    def _threshold_reached(self, events: list[dict[str, Any]]) -> bool:
        if len(events) >= MIN_EVENTS_FOR_DETECTION:
            return True
        start = parse_timestamp(events[0]["timestamp"])
        end = parse_timestamp(events[-1]["timestamp"])
        return int((end - start).total_seconds()) >= MIN_ACTIVITY_WINDOW_SECONDS

    def _strip_event_identifier(self, event: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in event.items() if key != "id"}

    def _build_tool_record(
        self,
        *,
        user_id: str,
        tool_id: str,
        detection: dict[str, Any],
        generated: dict[str, Any],
        artifact_id: str,
    ) -> ToolRecord:
        return ToolRecord(
            id=tool_id,
            user_id=user_id,
            name=generated["name"],
            description=generated["description"],
            created_at=utc_now(),
            source_event_window=SourceEventWindow.model_validate(
                {
                    "start": detection["event_window"]["start"],
                    "end": detection["event_window"]["end"],
                    "repetition_count": detection["repetition_count"],
                }
            ),
            trigger=ToolTrigger.model_validate(generated["trigger"]),
            transformation_summary=list(generated["transformation_summary"]),
            artifact=ToolArtifact(
                artifact_id=artifact_id,
                input_spec=ArtifactInputSpec.model_validate(generated["input_spec"]),
                output_spec=ArtifactOutputSpec.model_validate(generated["output_spec"]),
                primitives_used=list(generated["primitives_used"]),
                programmatic_interface=ProgrammaticInterface.model_validate(generated["programmatic_interface"]),
            ),
            ui_prefs=dict(generated["ui_prefs"]),
            stats=ToolStats(),
            status="ready",
            signature=detection["signature"],
        )
