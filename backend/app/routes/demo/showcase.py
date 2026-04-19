from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from backend.app.demo.gmail_live import sync_recent_messages


router = APIRouter(prefix="/demo/showcase", tags=["showcase"])


class DemoActionRequest(BaseModel):
    action: str
    detail: dict[str, Any] = Field(default_factory=dict)


class DemoToolRequest(BaseModel):
    request: str


class DemoEmailRequest(BaseModel):
    from_: str | None = Field(default=None, alias="from")
    subject: str
    body: str
    received_at: str | None = None


@router.get("/state")
def get_state(request: Request) -> dict[str, Any]:
    store = request.app.state.showcase_demo_store
    return store.load()


@router.post("/reset")
def reset_demo(request: Request) -> dict[str, Any]:
    store = request.app.state.showcase_demo_store
    return store.reset()


@router.post("/observe")
def record_action(payload: DemoActionRequest, request: Request) -> dict[str, Any]:
    store = request.app.state.showcase_demo_store
    return store.record_action(payload.action, payload.detail)


@router.post("/advance-day")
def advance_day(request: Request) -> dict[str, Any]:
    store = request.app.state.showcase_demo_store
    return store.advance_day()


@router.post("/tool/personalize")
def personalize_tool(payload: DemoToolRequest, request: Request) -> dict[str, Any]:
    store = request.app.state.showcase_demo_store
    return store.personalize_tool(payload.request)


@router.post("/tool/generate")
def generate_tool(request: Request) -> dict[str, Any]:
    store = request.app.state.showcase_demo_store
    return store.generate_tool()


@router.post("/tool/apply-pending")
def apply_pending_tool_update(request: Request) -> dict[str, Any]:
    store = request.app.state.showcase_demo_store
    return store.apply_pending_update()


@router.post("/inbox/inject")
def inject_email(payload: DemoEmailRequest, request: Request) -> dict[str, Any]:
    store = request.app.state.showcase_demo_store
    return store.inject_email(
        {
            "from": payload.from_,
            "subject": payload.subject,
            "body": payload.body,
            "received_at": payload.received_at,
        }
    )


@router.post("/inbox/sync-gmail")
def sync_gmail(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    store = request.app.state.showcase_demo_store
    result = sync_recent_messages(settings)
    if result["synced"]:
        state = store.load()
        known_ids = {message["id"] for message in state["inbox"]["messages"]}
        for message in reversed(result["messages"]):
            if message["id"] in known_ids:
                continue
            state = store.inject_email(message)
        return {"synced": True, "messages": result["messages"], "state": state}
    return result
