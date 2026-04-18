from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal


ROOT_DIR = Path(__file__).resolve().parents[1]


def _load_env_file() -> None:
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        os.environ.setdefault(key.strip(), value.strip())


def _bool_from_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AiSettings:
    mode: Literal["heuristic", "live", "hybrid"]
    api_key: str | None
    base_url: str
    model: str | None
    timeout_seconds: int
    mem0_mode: Literal["local", "remote", "hybrid"]
    mem0_base_url: str | None
    mem0_api_key: str | None

    @property
    def live_enabled(self) -> bool:
        return bool(self.api_key and self.model)


@lru_cache(maxsize=1)
def get_ai_settings() -> AiSettings:
    _load_env_file()

    mode = os.environ.get("PWA_AI_MODE", "hybrid").strip().lower()
    if mode not in {"heuristic", "live", "hybrid"}:
        mode = "hybrid"

    mem0_mode = os.environ.get("PWA_MEM0_MODE", "local").strip().lower()
    if mem0_mode not in {"local", "remote", "hybrid"}:
        mem0_mode = "local"

    return AiSettings(
        mode=mode,
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        model=os.environ.get("OPENAI_MODEL"),
        timeout_seconds=int(os.environ.get("PWA_AI_TIMEOUT_SECONDS", "20")),
        mem0_mode=mem0_mode,
        mem0_base_url=os.environ.get("PWA_MEM0_BASE_URL"),
        mem0_api_key=os.environ.get("PWA_MEM0_API_KEY"),
    )
