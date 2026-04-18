from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from backend.app.artifacts.store import ArtifactStore
from backend.app.config import Settings
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


def utc_now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class ToolRegistry:
    def __init__(self, repository: PlatformRepository, artifact_store: ArtifactStore, settings: Settings):
        self.repository = repository
        self.artifact_store = artifact_store
        self.settings = settings

    def ensure_seed_data(self) -> None:
        records = json.loads(Path(self.settings.seed_tools_path).read_text(encoding="utf-8"))
        runtime_html = Path(self.settings.runtime_template_path).read_text(encoding="utf-8")
        for raw_tool in records:
            if self.repository.get_tool(raw_tool["id"]) is not None:
                continue
            artifact_id, artifact_path = self.artifact_store.create_artifact(
                runtime_html,
                preferred_id=f"art_{raw_tool['id']}",
            )
            self.repository.store_artifact_record(
                artifact_id=artifact_id,
                user_id=raw_tool.get("user_id", "bob"),
                html_path=artifact_path,
            )
            tool = self._seed_record_to_tool(raw_tool=raw_tool, artifact_id=artifact_id)
            self.repository.save_tool(tool)

    def _seed_record_to_tool(self, raw_tool: dict[str, object], artifact_id: str) -> ToolRecord:
        return ToolRecord(
            id=str(raw_tool["id"]),
            user_id=str(raw_tool.get("user_id", "bob")),
            name=str(raw_tool["name"]),
            description=str(raw_tool["description"]),
            created_at=utc_now(),
            source_event_window=SourceEventWindow(
                start="2026-04-17T09:00:00Z",
                end="2026-04-17T09:20:00Z",
                repetition_count=3,
            ),
            trigger=ToolTrigger.model_validate(raw_tool["trigger"]),
            transformation_summary=[
                "Input: CSV of raw leads",
                "Filter to Series B+ in fintech",
                "Sort by company size descending",
                "Add outbound tag column",
                "Output: XLSX for CRM import",
            ],
            artifact=ToolArtifact(
                artifact_id=artifact_id,
                input_spec=ArtifactInputSpec(
                    primary_input="csv_file",
                    accepts=["paste", "file_drop", "file_picker"],
                    sample_fixture_id="domain_a_leads",
                ),
                output_spec=ArtifactOutputSpec(
                    format="xlsx",
                    filename_pattern="leads_{YYYY-MM-DD}.xlsx",
                ),
                primitives_used=["papaparse", "sheetjs"],
                programmatic_interface=ProgrammaticInterface(
                    input_type="csv_string",
                    output_type="xlsx_blob",
                ),
            ),
            ui_prefs={
                "theme": "dark",
                "density": "compact",
                "primary_label": "Format My Leads",
                "show_preview": True,
            },
            stats=ToolStats(),
            status="ready",
            signature=None,
        )
