from __future__ import annotations

from pathlib import Path
from uuid import uuid4


class ArtifactStore:
    def __init__(self, artifacts_dir: str | Path):
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def create_artifact(self, html_artifact: str, preferred_id: str | None = None) -> tuple[str, str]:
        artifact_id = preferred_id or f"art_{uuid4().hex[:10]}"
        artifact_path = self.artifacts_dir / f"{artifact_id}.html"
        artifact_path.write_text(html_artifact, encoding="utf-8")
        return artifact_id, str(artifact_path)

    def read_artifact(self, html_path: str) -> str:
        return Path(html_path).read_text(encoding="utf-8")
