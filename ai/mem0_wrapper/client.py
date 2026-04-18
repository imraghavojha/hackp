from __future__ import annotations


def get_user_preferences(user_id: str) -> str:
    return f"user={user_id}; theme=dark; density=compact"
