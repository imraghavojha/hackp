from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from backend.app.artifacts.validator import validate_html_artifact
from backend.app.contracts import InternalArtifactCreateRequest, InternalArtifactCreateResponse


router = APIRouter(prefix="/internal", tags=["artifacts"])


@router.post("/artifacts", response_model=InternalArtifactCreateResponse)
def create_artifact(payload: InternalArtifactCreateRequest, request: Request) -> InternalArtifactCreateResponse:
    repository = request.app.state.repository
    artifact_store = request.app.state.artifact_store
    validation = validate_html_artifact(payload.html_artifact)
    if not validation.is_valid:
        raise HTTPException(status_code=422, detail={"errors": validation.errors})
    artifact_id, artifact_path = artifact_store.create_artifact(payload.html_artifact)
    repository.store_artifact_record(artifact_id=artifact_id, user_id=payload.user_id, html_path=artifact_path)
    return InternalArtifactCreateResponse(artifact_id=artifact_id)


@router.get("/artifacts/{artifact_id}", response_class=HTMLResponse)
def get_artifact(artifact_id: str, request: Request) -> HTMLResponse:
    repository = request.app.state.repository
    artifact_store = request.app.state.artifact_store
    artifact_record = repository.get_artifact_record(artifact_id)
    if artifact_record is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return HTMLResponse(content=artifact_store.read_artifact(artifact_record["html_path"]))
