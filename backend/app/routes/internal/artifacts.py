from __future__ import annotations


def create_artifact(html_artifact: str) -> dict[str, str]:
    artifact_id = f"art_{len(html_artifact)}"
    return {"artifact_id": artifact_id}


def get_artifact(artifact_id: str) -> str:
    return f"runtime/shell/tool_template.html#artifact={artifact_id}"
