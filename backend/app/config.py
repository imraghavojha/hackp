from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    db_path: Path
    artifacts_dir: Path
    seed_tools_path: Path
    runtime_template_path: Path
    ai_base_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        db_path = Path(os.environ.get("PWA_DB_PATH", ROOT_DIR / "backend" / "data" / "platform.sqlite3"))
        artifacts_dir = Path(os.environ.get("PWA_ARTIFACTS_DIR", ROOT_DIR / "backend" / "data" / "artifacts"))
        seed_tools_path = Path(os.environ.get("PWA_SEED_TOOLS_PATH", ROOT_DIR / "fixtures" / "seed" / "tool_registry.json"))
        runtime_template_path = Path(
            os.environ.get("PWA_RUNTIME_TEMPLATE_PATH", ROOT_DIR / "runtime" / "shell" / "tool_template.html")
        )
        ai_base_url = os.environ.get("PWA_AI_BASE_URL", "http://127.0.0.1:8001")
        return cls(
            db_path=db_path,
            artifacts_dir=artifacts_dir,
            seed_tools_path=seed_tools_path,
            runtime_template_path=runtime_template_path,
            ai_base_url=ai_base_url.rstrip("/"),
        )
