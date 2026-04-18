from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from backend.app.contracts import AnalysisForUrlResponse, ToolsForUrlResponse, ToolUsageRequest, ToolUsageResponse
from backend.app.triggers.url_visit import matches_tool_trigger


router = APIRouter(prefix="/v1", tags=["tools"])


@router.get("/tools/for_url", response_model=ToolsForUrlResponse)
def get_tools_for_url(
    request: Request,
    url: str = Query(...),
    user_id: str = Query(...),
    allow_seed_fallback: bool = Query(False),
) -> ToolsForUrlResponse:
    repository = request.app.state.repository
    tools = [tool for tool in repository.list_ready_tools_for_url(user_id) if matches_tool_trigger(tool.trigger, url)]
    latest_analysis = repository.latest_analysis_for_url(user_id, url)

    generated_tools = [tool for tool in tools if tool.signature is not None]
    seed_tools = [tool for tool in tools if tool.signature is None]

    if generated_tools:
      return ToolsForUrlResponse(tools=generated_tools)

    if latest_analysis and latest_analysis.repetition_count >= 3:
        if latest_analysis.tool_id:
            matching = [tool for tool in tools if tool.id == latest_analysis.tool_id]
            if matching:
                return ToolsForUrlResponse(tools=matching)
        return ToolsForUrlResponse(tools=seed_tools)

    if allow_seed_fallback:
        return ToolsForUrlResponse(tools=seed_tools)

    return ToolsForUrlResponse(tools=[])


@router.get("/analysis/for_url", response_model=AnalysisForUrlResponse)
def get_analysis_for_url(
    request: Request,
    url: str = Query(...),
    user_id: str = Query(...),
) -> AnalysisForUrlResponse:
    repository = request.app.state.repository
    analysis = repository.latest_analysis_for_url(user_id, url)
    return AnalysisForUrlResponse(analysis=analysis)


@router.get("/tools/{tool_id}/artifact", response_class=HTMLResponse)
def get_tool_artifact(tool_id: str, request: Request) -> HTMLResponse:
    repository = request.app.state.repository
    artifact_store = request.app.state.artifact_store
    tool = repository.get_tool(tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")

    artifact_record = repository.get_artifact_record(tool.artifact.artifact_id)
    if artifact_record is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return HTMLResponse(content=artifact_store.read_artifact(artifact_record["html_path"]))


@router.post("/tools/{tool_id}/usage", response_model=ToolUsageResponse)
def post_tool_usage(tool_id: str, payload: ToolUsageRequest, request: Request) -> ToolUsageResponse:
    repository = request.app.state.repository
    logged = repository.log_tool_usage(
        tool_id=tool_id,
        user_id=payload.user_id,
        succeeded=payload.succeeded,
        duration_ms=payload.duration_ms,
    )
    return ToolUsageResponse(logged=logged)
