from __future__ import annotations

import json
from typing import Any

from ai.config import get_ai_settings
from ai.gemini_client import GeminiClient
from ai.k2_client import K2Client
from ai.openai_compatible import OpenAICompatibleClient, OpenAICompatibleError


def _get_live_client():
    settings = get_ai_settings()
    if settings.provider == "k2":
        return K2Client(settings)
    if settings.provider == "gemini":
        return GeminiClient(settings)
    return OpenAICompatibleClient(settings)


def summarize_showcase_state(payload: dict[str, Any]) -> dict[str, Any]:
    workflow = payload.get("workflow", {})
    tool = payload.get("tool", {})
    inbox = payload.get("inbox", {})
    history = payload.get("history", [])
    current_day = int(payload.get("current_day") or 1)

    times_seen = int(workflow.get("times_seen") or 0)
    workflow_name = str(workflow.get("name") or "Repeated workflow")
    pending_email = inbox.get("pending_update")
    heuristic = {
        "headline": f"Bob has repeated '{workflow_name}' {times_seen} time(s) across recent workdays.",
        "graph_note": (
            "The map connects Bob's deal export to the Excel prep pass and keeps those steps available "
            "for the next similar morning."
        ),
        "ai_caption": (
            f"The sidecar has enough context from {max(times_seen, 1)} recent pass(es) to prepare the workbook "
            f"the same way Bob already does it by hand."
        ),
        "pending_update_summary": (
            "A reviewer email is waiting to be merged into the sidecar."
            if pending_email
            else "No reviewer-requested sidecar changes are pending."
        ),
        "tool_summary": (
            f"Sidecar v{tool.get('version', 1)} keeps the primary action {tool.get('button_size', 'medium')} "
            f"and is tuned for Bob's shortlist-to-workbook pass."
        ),
    }

    settings = get_ai_settings()
    if settings.mode == "heuristic" or not settings.live_enabled:
        return heuristic

    prompt = {
        "current_day": current_day,
        "workflow": workflow,
        "tool": tool,
        "history": history[-12:],
        "pending_email": pending_email,
    }
    try:
        result = _get_live_client().chat_json(
            system_prompt=(
                "You summarize a product demo state for a workflow automation assistant.\n"
                "Return JSON only with keys: headline, graph_note, ai_caption, pending_update_summary, tool_summary.\n"
                "Be concise, polished, and grounded in the supplied state."
            ),
            user_prompt=f"Demo state:\n{json.dumps(prompt, indent=2)}",
            temperature=0.1,
            max_tokens=700,
        )
        parsed = result.parsed_json
        return {
            "headline": str(parsed.get("headline") or heuristic["headline"]),
            "graph_note": str(parsed.get("graph_note") or heuristic["graph_note"]),
            "ai_caption": str(parsed.get("ai_caption") or heuristic["ai_caption"]),
            "pending_update_summary": str(parsed.get("pending_update_summary") or heuristic["pending_update_summary"]),
            "tool_summary": str(parsed.get("tool_summary") or heuristic["tool_summary"]),
        }
    except (OpenAICompatibleError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return heuristic


def plan_showcase_tool_update(payload: dict[str, Any]) -> dict[str, Any]:
    request = str(payload.get("request") or "").strip()
    source = str(payload.get("source") or "user")
    tool = payload.get("tool", {})
    current_size = str(tool.get("button_size") or "medium")

    desired_size = current_size
    lowered = request.lower()
    if any(token in lowered for token in ("bigger", "larger", "large", "more prominent", "easier to click")):
        desired_size = "large"
    elif any(token in lowered for token in ("smaller", "compact", "less dominant")):
        desired_size = "small"

    heuristic = {
        "summary": (
            "The reviewer request can be folded into the sidecar as a focused update."
            if source == "email"
            else "Bob's preference can be applied as a lightweight sidecar update."
        ),
        "suggested_change": request or "Keep the sidecar aligned with Bob's workbook prep.",
        "button_size": desired_size,
        "primary_label": str(tool.get("primary_label") or "Prepare workbook"),
        "change_bullets": [
            "Preserve the learned export-to-workbook pass",
            "Update the main action styling to match the new request",
            "Keep the sidecar compact and reusable for future runs",
        ],
        "graph_note": (
            "The request becomes a new node in Bob's workflow memory and links to the sidecar version it changes."
        ),
    }

    settings = get_ai_settings()
    if settings.mode == "heuristic" or not settings.live_enabled:
        return heuristic

    prompt = {
        "source": source,
        "request": request,
        "tool": tool,
        "pending_email": payload.get("pending_email"),
    }
    try:
        result = _get_live_client().chat_json(
            system_prompt=(
                "You are planning a small update to a demo workflow tool.\n"
                "Return JSON only with keys: summary, suggested_change, button_size, primary_label, change_bullets, graph_note.\n"
                "button_size must be one of: small, medium, large.\n"
                "Keep the tool purpose intact; only suggest focused changes."
            ),
            user_prompt=f"Update request:\n{json.dumps(prompt, indent=2)}",
            temperature=0.1,
            max_tokens=700,
        )
        parsed = result.parsed_json
        button_size = str(parsed.get("button_size") or desired_size)
        if button_size not in {"small", "medium", "large"}:
            button_size = desired_size
        bullets = parsed.get("change_bullets", heuristic["change_bullets"])
        return {
            "summary": str(parsed.get("summary") or heuristic["summary"]),
            "suggested_change": str(parsed.get("suggested_change") or heuristic["suggested_change"]),
            "button_size": button_size,
            "primary_label": str(parsed.get("primary_label") or heuristic["primary_label"]),
            "change_bullets": [str(item) for item in bullets][:4] or heuristic["change_bullets"],
            "graph_note": str(parsed.get("graph_note") or heuristic["graph_note"]),
        }
    except (OpenAICompatibleError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return heuristic
