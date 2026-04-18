from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from ai.config import AiSettings, get_ai_settings


def get_user_preferences(user_id: str) -> str:
    return f"user={user_id}; theme=light; density=comfortable"


def _local_preference_lines(user_prefs_hint: str) -> list[str]:
    lines = [
        "tag_pattern=[Q2-Outbound-{industry}-{initials}]",
        "focus=keep the tool compact, clear, and enterprise-friendly",
    ]
    for raw_line in user_prefs_hint.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[") and "]" in line:
            line = line.split("]", maxsplit=1)[1].strip()
        lines.append(line)
    return lines


def _search_remote_preferences(user_id: str, settings: AiSettings) -> list[str]:
    if settings.mem0_mode == "local" or not settings.mem0_base_url:
        return []
    if not settings.mem0_api_key:
        return []

    url = f"{settings.mem0_base_url.rstrip('/')}/search?user_id={quote_plus(user_id)}&query={quote_plus('UI and transformation preferences')}&limit=10"
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {settings.mem0_api_key}",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=settings.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return []

    memories = payload.get("results", payload.get("memories", []))
    return [str(item.get("memory", "")).strip() for item in memories if isinstance(item, dict) and item.get("memory")]


def build_preferences_block(user_id: str, user_prefs_hint: str) -> str:
    settings = get_ai_settings()
    lines = [get_user_preferences(user_id), *_local_preference_lines(user_prefs_hint)]
    if settings.mem0_mode in {"remote", "hybrid"}:
        lines.extend(_search_remote_preferences(user_id, settings))
    return "\n".join(dict.fromkeys(line for line in lines if line))


def infer_theme(preferences_block: str) -> str:
    if "theme=dark" in preferences_block.lower() or "dark mode" in preferences_block.lower():
        return "dark"
    return "light"


def infer_density(preferences_block: str) -> str:
    if "compact" in preferences_block.lower():
        return "compact"
    return "comfortable"


def infer_initials(user_id: str, preferences_block: str) -> str:
    lowered = preferences_block.lower()
    marker = "initials="
    if marker in lowered:
        fragment = preferences_block[lowered.index(marker) + len(marker) :]
        return fragment.splitlines()[0].split(";")[0].strip().upper()[:4] or user_id[:2].upper()
    return user_id[:2].upper()


def infer_tag_pattern(preferences_block: str) -> str:
    marker = "tag_pattern="
    lowered = preferences_block.lower()
    if marker in lowered:
        fragment = preferences_block[lowered.index(marker) + len(marker) :]
        return fragment.splitlines()[0].strip()
    return "[Q2-Outbound-{industry}-{initials}]"
