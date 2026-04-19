from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from backend.app.config import Settings


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _decode_parts(parts: list[dict[str, Any]]) -> str:
    for part in parts:
        mime_type = part.get("mimeType")
        body = part.get("body", {})
        data = body.get("data")
        if mime_type == "text/plain" and data:
            try:
                return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                return ""
        nested = part.get("parts", [])
        if nested:
            decoded = _decode_parts(nested)
            if decoded:
                return decoded
    return ""


def _load_credentials(settings: Settings) -> Credentials | None:
    token_path = settings.demo_gmail_token_path
    if token_path is None or not token_path.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleRequest())
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def sync_recent_messages(settings: Settings, *, max_results: int = 5) -> dict[str, Any]:
    if settings.demo_gmail_credentials_path is None or settings.demo_gmail_token_path is None:
        return {"synced": False, "reason": "missing_credentials", "messages": []}
    if not settings.demo_gmail_token_path.exists():
        return {"synced": False, "reason": "missing_token", "messages": []}

    creds = _load_credentials(settings)
    if creds is None:
        return {"synced": False, "reason": "unable_to_load_credentials", "messages": []}

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    response = (
        service.users()
        .messages()
        .list(userId="me", q=settings.demo_gmail_query, maxResults=max_results)
        .execute()
    )
    messages = []
    for item in response.get("messages", []):
        detail = (
            service.users()
            .messages()
            .get(userId="me", id=item["id"], format="full")
            .execute()
        )
        headers = {
            header.get("name", "").lower(): header.get("value", "")
            for header in detail.get("payload", {}).get("headers", [])
        }
        snippet = detail.get("snippet", "")
        body = _decode_parts(detail.get("payload", {}).get("parts", [])) or snippet
        messages.append(
            {
                "id": detail.get("id"),
                "from": headers.get("from", ""),
                "subject": headers.get("subject", "(no subject)"),
                "body": body,
                "received_at": headers.get("date", ""),
            }
        )
    return {"synced": True, "reason": "ok", "messages": messages}
