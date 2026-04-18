from __future__ import annotations

import json
from urllib.parse import urlparse
from typing import Any

from ai.config import get_ai_settings
from ai.contracts import DetectionRequest, GenerateToolRequest
from ai.fallbacks import (
    DOMAIN_DEFINITIONS,
    build_detection_response,
    build_generate_response,
    classify_domain_from_events,
    domain_from_signature,
    heuristic_generate_response,
    infer_repetition_count,
)
from ai.mem0_wrapper.client import (
    build_preferences_block,
    infer_density,
    infer_initials,
    infer_tag_pattern,
    infer_theme,
)
from ai.gemini_client import GeminiClient
from ai.k2_client import K2Client
from ai.openai_compatible import OpenAICompatibleClient, OpenAICompatibleError
from ai.prompts.detect import DETECT_SYSTEM_PROMPT, GENERIC_DETECT_SYSTEM_PROMPT
from ai.prompts.generate import GENERATE_SYSTEM_PROMPT


def _get_live_client():
    settings = get_ai_settings()
    if settings.provider == "k2":
        return K2Client(settings)
    if settings.provider == "gemini":
        return GeminiClient(settings)
    return OpenAICompatibleClient(settings)


def detect_transformation(payload: dict[str, Any]) -> dict[str, Any]:
    request = DetectionRequest.model_validate(payload)
    domain = classify_domain_from_events(request.events)
    settings = get_ai_settings()
    events_json = [event.model_dump(mode="json") for event in request.events]
    if domain is None:
        if len(events_json) < 3:
            return {"detected": False}
        return _generic_activity_analysis(events_json, settings)

    signature = DOMAIN_DEFINITIONS[domain]["signature"]
    if signature in request.existing_tool_signatures:
        return {"detected": False}

    critical_events = [event for event in request.events if event.event_type in {"copy", "paste", "input", "submit", "file_download"}]
    if len(critical_events) < 2:
        return {"detected": False}

    heuristic = build_detection_response(domain=domain, events=events_json, confidence=0.78)
    if settings.mode == "heuristic" or not settings.live_enabled:
        return heuristic

    client = _get_live_client()
    try:
        result = client.chat_json(
            system_prompt=DETECT_SYSTEM_PROMPT,
            user_prompt=_build_detect_prompt(domain=domain, payload=request.model_dump(mode="json")),
            temperature=0.0,
            max_tokens=700,
        )
        parsed = result.parsed_json
        if not parsed.get("detected", False):
            return {"detected": False}
        return build_detection_response(
            domain=domain,
            events=events_json,
            confidence=float(parsed.get("confidence", heuristic["confidence"])),
            summary=str(parsed.get("summary") or heuristic["summary"]),
        ) | {
            "input_characterization": str(parsed.get("input_characterization") or heuristic["input_characterization"]),
            "output_characterization": str(parsed.get("output_characterization") or heuristic["output_characterization"]),
            "repetition_count": max(2, int(parsed.get("repetition_count", heuristic["repetition_count"]))),
        }
    except (OpenAICompatibleError, ValueError, TypeError):
        return heuristic


def generate_tool(payload: dict[str, Any]) -> dict[str, Any]:
    request = GenerateToolRequest.model_validate(payload)
    domain = domain_from_signature(request.detection.get("signature"))
    if domain is None:
        domain = classify_domain_from_events(request.events)
    if domain is None:
        raise ValueError("Unable to determine tool domain from detection payload")

    preferences_block = build_preferences_block(request.user_id, request.user_prefs_hint)
    theme = infer_theme(preferences_block)
    density = infer_density(preferences_block)
    initials = infer_initials(request.user_id, preferences_block)
    tag_pattern = infer_tag_pattern(preferences_block)

    settings = get_ai_settings()
    if settings.mode == "heuristic" or not settings.live_enabled:
        return heuristic_generate_response(domain, theme=theme, density=density, initials=initials, tag_pattern=tag_pattern)

    client = _get_live_client()
    try:
        result = client.chat_json(
            system_prompt=GENERATE_SYSTEM_PROMPT,
            user_prompt=_build_generate_prompt(
                domain=domain,
                detection=request.detection,
                events=[event.model_dump(mode="json") for event in request.events],
                preferences_block=preferences_block,
            ),
            temperature=0.15,
            max_tokens=1_200,
        )
        blueprint = _normalize_blueprint(
            domain=domain,
            blueprint=result.parsed_json,
            theme=theme,
            density=density,
            initials=initials,
            tag_pattern=tag_pattern,
        )
        return build_generate_response(
            domain=domain,
            name=blueprint["name"],
            description=blueprint["description"],
            transformation_summary=blueprint["transformation_summary"],
            trigger_prompt=blueprint["trigger_prompt"],
            ui_prefs=blueprint["ui_prefs"],
            default_config=blueprint["default_config"],
        )
    except (OpenAICompatibleError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return heuristic_generate_response(domain, theme=theme, density=density, initials=initials, tag_pattern=tag_pattern)


def _build_detect_prompt(*, domain: str, payload: dict[str, Any]) -> str:
    definition = DOMAIN_DEFINITIONS[domain]
    return (
        f"Known domain: {domain}\n"
        f"Expected URL pattern: {definition['url_pattern']}\n"
        "Determine whether these events show a repeated transformation worth generating a tool for.\n"
        "Return JSON only.\n\n"
        f"Payload:\n{json.dumps(payload, indent=2)}"
    )


def _build_generic_detect_prompt(payload: dict[str, Any]) -> str:
    return (
        "You are analyzing generic browser activity.\n"
        "Summarize what the user appears to be doing on the current page.\n"
        "Do not invent productivity if the behavior looks exploratory.\n"
        "Return JSON only with keys: detected, confidence, summary, input_characterization, output_characterization, repetition_count.\n\n"
        f"Payload:\n{json.dumps(payload, indent=2)}"
    )


def _build_generate_prompt(*, domain: str, detection: dict[str, Any], events: list[dict[str, Any]], preferences_block: str) -> str:
    definition = DOMAIN_DEFINITIONS[domain]
    return (
        f"Known domain: {domain}\n"
        f"Domain defaults: {json.dumps(definition, indent=2)}\n"
        "Return only the JSON blueprint requested by the system prompt.\n"
        "Do not return HTML.\n\n"
        f"Detection:\n{json.dumps(detection, indent=2)}\n\n"
        f"Events:\n{json.dumps(events[:12], indent=2)}\n\n"
        f"User preferences:\n{preferences_block}"
    )


def _normalize_blueprint(
    *,
    domain: str,
    blueprint: dict[str, Any],
    theme: str,
    density: str,
    initials: str,
    tag_pattern: str,
) -> dict[str, Any]:
    definition = DOMAIN_DEFINITIONS[domain]
    default_config = {**definition["default_config"]}
    if domain == "domain_a":
        default_config["initials"] = initials
        default_config["tag_pattern"] = tag_pattern

    provided_config = blueprint.get("default_config", {})
    if isinstance(provided_config, dict):
        default_config.update(provided_config)

    ui_prefs = blueprint.get("ui_prefs", {})
    return {
        "name": str(blueprint.get("name") or definition["name"]),
        "description": str(blueprint.get("description") or definition["summary"]),
        "transformation_summary": [
            str(item)
            for item in blueprint.get("transformation_summary", definition["transformation_summary"])
        ],
        "trigger_prompt": str(blueprint.get("trigger_prompt") or definition["default_prompt"]),
        "ui_prefs": {
            "theme": str(ui_prefs.get("theme") or theme),
            "density": str(ui_prefs.get("density") or density),
            "primary_label": str(ui_prefs.get("primary_label") or definition["primary_label"]),
        },
        "default_config": default_config,
    }


def _generic_activity_analysis(events: list[dict[str, Any]], settings) -> dict[str, Any]:
    current_url = str(events[-1]["url"])
    parsed_url = urlparse(current_url)
    host = parsed_url.netloc or current_url
    repetition_count = max(1, infer_repetition_count(events))
    heuristic = {
        "detected": True,
        "signature": None,
        "confidence": 0.62,
        "transformation_name": "Observed browser activity",
        "summary": f"Bob appears to be reading and interacting with content on {host} as part of a repeated browser workflow.",
        "input_characterization": "Browser page content and copied/pasted text",
        "output_characterization": "No dedicated helper generated yet; activity captured for analysis",
        "event_window": {
            "start": events[0]["timestamp"],
            "end": events[-1]["timestamp"],
        },
        "repetition_count": repetition_count,
    }
    if settings.mode == "heuristic" or not settings.live_enabled:
        return heuristic

    client = _get_live_client()
    try:
        result = client.chat_json(
            system_prompt=GENERIC_DETECT_SYSTEM_PROMPT,
            user_prompt=_build_generic_detect_prompt(
                {
                    "user_id": events[0]["user_id"],
                    "events": events[-12:],
                    "existing_tool_signatures": [],
                }
            ),
            temperature=0.0,
            max_tokens=500,
        )
        parsed = result.parsed_json
        return {
            "detected": True,
            "signature": None,
            "confidence": float(parsed.get("confidence", heuristic["confidence"])),
            "transformation_name": "Observed browser activity",
            "summary": str(parsed.get("summary") or heuristic["summary"]),
            "input_characterization": str(parsed.get("input_characterization") or heuristic["input_characterization"]),
            "output_characterization": str(parsed.get("output_characterization") or heuristic["output_characterization"]),
            "event_window": heuristic["event_window"],
            "repetition_count": max(repetition_count, int(parsed.get("repetition_count", heuristic["repetition_count"]))),
        }
    except (OpenAICompatibleError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return heuristic
