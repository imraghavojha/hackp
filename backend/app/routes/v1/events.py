from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.contracts import EventsBatchRequest, EventsBatchResponse


router = APIRouter(prefix="/v1", tags=["events"])


@router.post("/events", response_model=EventsBatchResponse)
def post_events(payload: EventsBatchRequest, request: Request) -> EventsBatchResponse:
    repository = request.app.state.repository
    scheduler = request.app.state.scheduler
    accepted = repository.insert_events(payload.user_id, payload.events)
    scheduler.maybe_process_user(payload.user_id)
    buffered = repository.count_pending_events(payload.user_id)
    return EventsBatchResponse(accepted=accepted, buffered=buffered)
