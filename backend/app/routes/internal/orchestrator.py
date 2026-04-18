from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.contracts import OrchestratorRunRequest, OrchestratorRunResponse


router = APIRouter(prefix="/internal/orchestrator", tags=["orchestrator"])


@router.post("/run_tool", response_model=OrchestratorRunResponse)
def run_tool(payload: OrchestratorRunRequest, request: Request) -> OrchestratorRunResponse:
    orchestrator = request.app.state.orchestrator
    return orchestrator.run_tool(
        tool_id=payload.tool_id,
        user_id=payload.user_id,
        input_data=payload.input_data,
        config_override=payload.config_override,
    )
