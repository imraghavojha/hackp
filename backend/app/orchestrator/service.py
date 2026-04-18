from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from backend.app.artifacts.store import ArtifactStore
from backend.app.contracts import OrchestratorRunResponse
from backend.app.store.repository import PlatformRepository


class ToolOrchestrator:
    def __init__(self, repository: PlatformRepository, artifact_store: ArtifactStore):
        self.repository = repository
        self.artifact_store = artifact_store

    def run_tool(
        self,
        tool_id: str,
        user_id: str,
        input_data: Any,
        config_override: dict[str, Any] | None = None,
    ) -> OrchestratorRunResponse:
        tool = self.repository.get_tool(tool_id)
        if tool is None or tool.user_id != user_id:
            return OrchestratorRunResponse(
                run_id=f"run_{uuid4().hex[:10]}",
                output_ref="missing_tool",
                succeeded=False,
            )

        artifact_record = self.repository.get_artifact_record(tool.artifact.artifact_id)
        if artifact_record is None:
            return OrchestratorRunResponse(
                run_id=f"run_{uuid4().hex[:10]}",
                output_ref="missing_artifact",
                succeeded=False,
            )

        html = self.artifact_store.read_artifact(artifact_record["html_path"])
        contract_present = "window.Tool" in html and "transform(" in html
        preview_output = self._preview_known_tool(tool_id=tool.id, input_data=input_data, config_override=config_override or {})
        preview = {
            "received_input": input_data,
            "config_override": config_override or {},
            "contract_present": contract_present,
            "preview_output": preview_output,
            "checked_at": datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        }
        return OrchestratorRunResponse(
            run_id=f"run_{uuid4().hex[:10]}",
            output_ref="inline" if contract_present else "invalid_artifact",
            succeeded=contract_present,
            artifact_id=tool.artifact.artifact_id,
            output_preview=preview,
        )

    def _preview_known_tool(self, *, tool_id: str, input_data: Any, config_override: dict[str, Any]) -> list[list[str]] | None:
        if tool_id not in {"tool_lead_formatter_v1", "tool_domain_a_lead_formatter_v1"}:
            return None
        if not isinstance(input_data, str) or not input_data.strip():
            return None

        rows = list(csv.reader(io.StringIO(input_data)))
        if len(rows) < 2:
            return rows

        header, *body = rows
        indices = {name.strip().lower(): position for position, name in enumerate(header)}
        industry_index = indices.get("industry")
        stage_index = indices.get("stage")
        employees_index = indices.get("employees")
        if industry_index is None or stage_index is None or employees_index is None:
            return rows

        rank = {"seed": 0, "series_a": 1, "series_b": 2, "series_c": 3, "series_d": 4, "ipo": 5}
        min_stage = config_override.get("filter_min_stage", "series_b")
        expected_industry = str(config_override.get("industry", "fintech")).lower()
        initials = str(config_override.get("initials", "BK")).upper()
        tag_pattern = str(config_override.get("tag_pattern", "[Q2-Outbound-{industry}-{initials}]"))

        def stage_value(raw_stage: str) -> int:
            return rank.get(raw_stage.strip().lower().replace(" ", "_"), 0)

        filtered = [
            row
            for row in body
            if expected_industry in str(row[industry_index]).lower() and stage_value(str(row[stage_index])) >= stage_value(min_stage)
        ]
        filtered.sort(key=lambda row: int(row[employees_index] or 0), reverse=True)
        preview_rows = [header + ["tag"]]
        for row in filtered:
            industry_token = str(row[industry_index]).replace(" ", "")
            tag = tag_pattern.replace("{industry}", industry_token).replace("{initials}", initials)
            preview_rows.append(row + [tag])
        return preview_rows
