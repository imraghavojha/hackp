from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.contracts import FeedbackRequest, FeedbackResponse


router = APIRouter(prefix="/v1", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
def post_feedback(payload: FeedbackRequest, request: Request) -> FeedbackResponse:
    repository = request.app.state.repository
    memory_id = repository.store_feedback(payload)
    return FeedbackResponse(stored=True, memory_id=memory_id)
