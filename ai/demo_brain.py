from __future__ import annotations

import json
import re
from typing import Any

from ai.config import get_ai_settings
from ai.gemini_client import GeminiClient
from ai.k2_client import K2Client
from ai.openai_compatible import OpenAICompatibleClient, OpenAICompatibleError


STAGE_LABELS = {
    "series c": "Series C",
    "series b": "Series B",
    "growth": "Growth",
    "seed": "Seed",
}


def _get_live_client():
    settings = get_ai_settings()
    if settings.provider == "k2":
        return K2Client(settings)
    if settings.provider == "gemini":
        return GeminiClient(settings)
    return OpenAICompatibleClient(settings)


def _default_recipe(recipe: dict[str, Any] | None = None) -> dict[str, Any]:
    base = {
        "column_name": "Priority",
        "formula_kind": "threshold",
        "formula_text": '=IF(D2>=200,"Tier 1","Tier 2")',
        "fill_range": "G2:G7",
        "source_field": "employees",
        "source_column_letter": "D",
        "operator": ">=",
        "threshold": 200,
        "match_value": None,
        "true_value": "Tier 1",
        "false_value": "Tier 2",
        "output_filename": "fintech_shortlist_prepped.xlsx",
    }
    if recipe:
        for key, value in recipe.items():
            if value is not None:
                base[key] = value
    return base


def _flatten_quotes(request: str) -> list[str]:
    matches = re.findall(r'"([^"]+)"|\'([^\']+)\'', request)
    values: list[str] = []
    for left, right in matches:
        if left:
            values.append(left.strip())
        if right:
            values.append(right.strip())
    return [value for value in values if value]


def _titleize_label(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value.strip())
    if not cleaned:
        return cleaned
    return " ".join(part.capitalize() if part.islower() else part for part in cleaned.split(" "))


def _extract_column_name(request: str, fallback: str) -> str:
    lowered = request.lower()
    explicit = re.search(r"(?:column|field)\s+(?:called|named)?\s*[\"']?([a-z][a-z0-9 _/-]{1,30})", lowered)
    if explicit:
        return _titleize_label(explicit.group(1))
    if "follow up" in lowered or "follow-up" in lowered:
        return "Follow Up"
    if "coverage lane" in lowered or "lane" in lowered:
        return "Coverage Lane"
    if "revision" in lowered:
        return "Analyst Revision"
    if "priority" in lowered:
        return "Priority"
    return fallback


def _extract_labels(request: str, fallback_true: str, fallback_false: str) -> tuple[str, str]:
    quoted = _flatten_quotes(request)
    if len(quoted) >= 2:
        return _titleize_label(quoted[0]), _titleize_label(quoted[1])

    lowered = request.lower()
    pairs = [
        ("tier 1", "tier 2"),
        ("hot", "watch"),
        ("fast track", "review"),
        ("priority", "monitor"),
        ("green", "hold"),
    ]
    for high, low in pairs:
        if high in lowered and low in lowered:
            return _titleize_label(high), _titleize_label(low)

    top_match = re.search(r"(?:mark|label|set).+?as\s+([a-z0-9 -]{3,24})\s+(?:and|vs\.?|versus)\s+([a-z0-9 -]{3,24})", lowered)
    if top_match:
        return _titleize_label(top_match.group(1)), _titleize_label(top_match.group(2))

    return fallback_true, fallback_false


def _find_stage_label(request: str) -> str | None:
    lowered = request.lower()
    for token, label in STAGE_LABELS.items():
        if token in lowered:
            return label
    return None


def _build_formula_text(recipe: dict[str, Any]) -> str:
    if recipe.get("formula_kind") == "stage_match":
        match_value = recipe.get("match_value") or "Series C"
        true_value = recipe.get("true_value") or "Fast Track"
        false_value = recipe.get("false_value") or "Review"
        return f'=IF(C2="{match_value}","{true_value}","{false_value}")'

    threshold = int(recipe.get("threshold") or 200)
    operator = recipe.get("operator") or ">="
    true_value = recipe.get("true_value") or "Tier 1"
    false_value = recipe.get("false_value") or "Tier 2"
    return f'=IF(D2{operator}{threshold},"{true_value}","{false_value}")'


def _heuristic_recipe_patch(request: str, current_recipe: dict[str, Any]) -> dict[str, Any]:
    recipe = _default_recipe(current_recipe)
    lowered = request.lower()

    recipe["column_name"] = _extract_column_name(request, str(recipe.get("column_name") or "Priority"))
    true_value, false_value = _extract_labels(
        request,
        str(recipe.get("true_value") or "Tier 1"),
        str(recipe.get("false_value") or "Tier 2"),
    )
    recipe["true_value"] = true_value
    recipe["false_value"] = false_value

    stage_label = _find_stage_label(request)
    number_match = re.search(r"\b(\d{2,4})\b", lowered)
    uses_headcount = any(token in lowered for token in ("employee", "employees", "headcount", "threshold", ">=", "at least", "over"))

    if stage_label and "employee" not in lowered and "headcount" not in lowered:
        recipe["formula_kind"] = "stage_match"
        recipe["source_field"] = "stage"
        recipe["source_column_letter"] = "C"
        recipe["operator"] = "="
        recipe["match_value"] = stage_label
    elif uses_headcount or number_match:
        recipe["formula_kind"] = "threshold"
        recipe["source_field"] = "employees"
        recipe["source_column_letter"] = "D"
        recipe["operator"] = ">="
        if number_match:
            recipe["threshold"] = int(number_match.group(1))
        recipe["match_value"] = None

    recipe["formula_text"] = _build_formula_text(recipe)
    return recipe


def _recipe_patch_summary(recipe: dict[str, Any]) -> str:
    column_name = recipe.get("column_name") or "Priority"
    return f"Update the {column_name} column to use {recipe.get('formula_text')} and fill it down automatically."


def _tool_ready_caption(recipe: dict[str, Any]) -> str:
    column_name = recipe.get("column_name") or "Priority"
    formula_text = recipe.get("formula_text") or _build_formula_text(recipe)
    return f"The sidecar can take a CSV, add the {column_name} column, and apply {formula_text} before reopening the workbook."


def summarize_showcase_state(payload: dict[str, Any]) -> dict[str, Any]:
    workflow = payload.get("workflow", {})
    tool = payload.get("tool", {})
    inbox = payload.get("inbox", {})
    workbook = payload.get("workbook", {})
    scenes = payload.get("scenes", {})

    times_seen = int(workflow.get("times_seen") or 0)
    workflow_name = str(workflow.get("name") or "Repeated workflow")
    current_day = int(payload.get("current_day") or 1)
    recipe = _default_recipe(tool.get("recipe"))
    column_name = str(recipe.get("column_name") or "Priority")
    formula_text = str(recipe.get("formula_text") or _build_formula_text(recipe))
    pending_email = inbox.get("pending_update")
    tool_generated = bool(scenes.get("tool_generated"))
    tool_updated = bool(scenes.get("analyst_update_applied"))
    manual_context_seen = bool(workbook.get("column_added") or workbook.get("formula_seeded") or times_seen)

    if pending_email:
        pending_summary = f"Reviewer request waiting: {pending_email.get('suggested_change') or pending_email.get('summary')}"
    else:
        pending_summary = "No reviewer-requested tool changes are pending."

    if tool_updated:
        ai_caption = f"The tool now uses the latest workbook rule: {formula_text}."
    elif tool_generated:
        ai_caption = _tool_ready_caption(recipe)
    elif current_day >= 2 and times_seen >= 1:
        ai_caption = f"I noticed Bob keeps adding {column_name} by hand. Want me to add code for that and turn the CSV into a ready-made workbook?"
    elif manual_context_seen:
        ai_caption = f"The map captured Bob's {column_name} formula and is holding that context until the tool is created."
    else:
        ai_caption = f"Once Bob finishes the workbook pass, Vim can learn the {workflow_name.lower()} pattern."

    heuristic = {
        "headline": f"Bob has repeated '{workflow_name}' {times_seen} time(s); the latest context centers on the {column_name} formula.",
        "graph_note": (
            f"The graph follows the export, the Excel edits, and the remembered rule {formula_text} so the next similar morning can become a tool."
        ),
        "ai_caption": ai_caption,
        "pending_update_summary": pending_summary,
        "tool_summary": (
            f"Sidecar v{tool.get('version', 1)} is {tool.get('status', 'observing')} and currently targets {column_name} with {formula_text}."
        ),
    }

    settings = get_ai_settings()
    if settings.mode == "heuristic" or not settings.live_enabled:
        return heuristic

    prompt = {
        "current_day": current_day,
        "workflow": workflow,
        "tool": tool,
        "workbook": workbook,
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
    current_recipe = _default_recipe(tool.get("recipe"))
    current_size = str(tool.get("button_size") or "medium")
    tool_generated = bool(payload.get("tool_generated") or payload.get("scenes", {}).get("tool_generated"))

    desired_size = current_size
    lowered = request.lower()
    if any(token in lowered for token in ("bigger", "larger", "large", "more prominent", "easier to click")):
        desired_size = "large"
    elif any(token in lowered for token in ("smaller", "compact", "less dominant")):
        desired_size = "small"

    heuristic_recipe = _heuristic_recipe_patch(request or "", current_recipe)
    heuristic = {
        "summary": (
            "The reviewer request can be folded into the CSV-to-workbook tool as a formula update."
            if source == "email"
            else "Bob's request can be applied as a focused tool update."
        ),
        "suggested_change": _recipe_patch_summary(heuristic_recipe),
        "button_size": desired_size,
        "primary_label": "Convert CSV to workbook" if tool_generated else "Add code",
        "change_bullets": [
            "Preserve the observed CSV to Excel flow",
            f"Write the {heuristic_recipe['column_name']} column automatically",
            f"Seed {heuristic_recipe['formula_text']} and fill it down for the imported rows",
        ],
        "graph_note": (
            "The new request becomes a possible workflow revision and links directly to the formula stored in the tool."
        ),
        "recipe_patch": heuristic_recipe,
    }

    settings = get_ai_settings()
    if settings.mode == "heuristic" or not settings.live_enabled:
        return heuristic

    prompt = {
        "source": source,
        "request": request,
        "tool": tool,
        "current_recipe": current_recipe,
        "pending_email": payload.get("pending_email"),
    }
    try:
        result = _get_live_client().chat_json(
            system_prompt=(
                "You are planning a small update to a demo CSV-to-Excel workflow tool.\n"
                "Return JSON only with keys: summary, suggested_change, button_size, primary_label, change_bullets, graph_note, recipe_patch.\n"
                "button_size must be one of: small, medium, large.\n"
                "recipe_patch must be an object with keys: column_name, formula_kind, formula_text, fill_range, source_field, source_column_letter, operator, threshold, match_value, true_value, false_value, output_filename.\n"
                "Keep the tool purpose intact; only suggest focused changes."
            ),
            user_prompt=f"Update request:\n{json.dumps(prompt, indent=2)}",
            temperature=0.1,
            max_tokens=900,
        )
        parsed = result.parsed_json
        button_size = str(parsed.get("button_size") or desired_size)
        if button_size not in {"small", "medium", "large"}:
            button_size = desired_size

        recipe_patch = parsed.get("recipe_patch", {})
        if not isinstance(recipe_patch, dict):
            recipe_patch = {}
        merged_recipe = _default_recipe(current_recipe)
        for key, value in recipe_patch.items():
            if value is not None:
                merged_recipe[key] = value
        if not merged_recipe.get("formula_text"):
            merged_recipe["formula_text"] = _build_formula_text(merged_recipe)

        bullets = parsed.get("change_bullets", heuristic["change_bullets"])
        return {
            "summary": str(parsed.get("summary") or heuristic["summary"]),
            "suggested_change": str(parsed.get("suggested_change") or _recipe_patch_summary(merged_recipe)),
            "button_size": button_size,
            "primary_label": str(parsed.get("primary_label") or heuristic["primary_label"]),
            "change_bullets": [str(item) for item in bullets][:4] or heuristic["change_bullets"],
            "graph_note": str(parsed.get("graph_note") or heuristic["graph_note"]),
            "recipe_patch": merged_recipe,
        }
    except (OpenAICompatibleError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return heuristic
