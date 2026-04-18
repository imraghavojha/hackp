from __future__ import annotations


def get_user_preferences(user_id: str) -> str:
    return f"user={user_id}; theme=dark; density=compact"


def build_preferences_block(user_id: str, user_prefs_hint: str) -> str:
    lines = [
        get_user_preferences(user_id),
        "tag_pattern=[Q2-Outbound-{industry}-{initials}]",
        "focus=keep the tool compact and obvious to use",
    ]
    if user_prefs_hint.strip():
        lines.append(user_prefs_hint.strip())
    return "\n".join(lines)


def infer_theme(preferences_block: str) -> str:
    if "theme=light" in preferences_block.lower() or "light mode" in preferences_block.lower():
        return "light"
    return "dark"


def infer_density(preferences_block: str) -> str:
    if "comfortable" in preferences_block.lower():
        return "comfortable"
    return "compact"


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
