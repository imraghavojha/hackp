from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


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
class Settings:
    db_path: Path
    artifacts_dir: Path
    seed_tools_path: Path
    runtime_template_path: Path
    demo_state_path: Path
    ai_base_url: str
    scheduler_enabled: bool
    scheduler_interval_seconds: int
    detection_min_events: int
    detection_min_activity_window_seconds: int
    detection_min_repetitions: int
    demo_gmail_credentials_path: Path | None
    demo_gmail_token_path: Path | None
    demo_gmail_query: str

    @classmethod
    def from_env(cls) -> "Settings":
        _load_env_file()
        db_path = Path(os.environ.get("PWA_DB_PATH", ROOT_DIR / "backend" / "data" / "platform.sqlite3"))
        artifacts_dir = Path(os.environ.get("PWA_ARTIFACTS_DIR", ROOT_DIR / "backend" / "data" / "artifacts"))
        seed_tools_path = Path(os.environ.get("PWA_SEED_TOOLS_PATH", ROOT_DIR / "fixtures" / "seed" / "tool_registry.json"))
        runtime_template_path = Path(
            os.environ.get("PWA_RUNTIME_TEMPLATE_PATH", ROOT_DIR / "runtime" / "shell" / "tool_template.html")
        )
        demo_state_path = Path(os.environ.get("PWA_DEMO_STATE_PATH", ROOT_DIR / "backend" / "data" / "showcase_demo.json"))
        ai_base_url = os.environ.get("PWA_AI_BASE_URL", "http://127.0.0.1:8001")
        gmail_credentials = os.environ.get("PWA_DEMO_GMAIL_CREDENTIALS_PATH")
        gmail_token = os.environ.get("PWA_DEMO_GMAIL_TOKEN_PATH")
        return cls(
            db_path=db_path,
            artifacts_dir=artifacts_dir,
            seed_tools_path=seed_tools_path,
            runtime_template_path=runtime_template_path,
            demo_state_path=demo_state_path,
            ai_base_url=ai_base_url.rstrip("/"),
            scheduler_enabled=_bool_from_env("PWA_SCHEDULER_ENABLED", True),
            scheduler_interval_seconds=int(os.environ.get("PWA_SCHEDULER_INTERVAL_SECONDS", "120")),
            detection_min_events=int(os.environ.get("PWA_DETECTION_MIN_EVENTS", "50")),
            detection_min_activity_window_seconds=int(os.environ.get("PWA_DETECTION_MIN_ACTIVITY_WINDOW_SECONDS", "600")),
            detection_min_repetitions=int(os.environ.get("PWA_DETECTION_MIN_REPETITIONS", "3")),
            demo_gmail_credentials_path=Path(gmail_credentials).expanduser() if gmail_credentials else None,
            demo_gmail_token_path=Path(gmail_token).expanduser() if gmail_token else None,
            demo_gmail_query=os.environ.get("PWA_DEMO_GMAIL_QUERY", "is:unread newer_than:14d"),
        )
