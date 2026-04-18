from __future__ import annotations

import re
from dataclasses import dataclass, field


WINDOW_TOOL_RE = re.compile(r"window\.Tool\s*=\s*(window\.Tool\s*\|\|\s*)?\{", re.MULTILINE)
TRANSFORM_RE = re.compile(r"(async\s+)?transform\s*\(", re.MULTILINE)
METADATA_RE = re.compile(r"metadata\s*:", re.MULTILINE)
DEFAULT_CONFIG_RE = re.compile(r"defaultConfig\s*:", re.MULTILINE)
INPUT_TYPE_RE = re.compile(r"[\"']?input_type[\"']?\s*:", re.MULTILINE)
OUTPUT_TYPE_RE = re.compile(r"[\"']?output_type[\"']?\s*:", re.MULTILINE)


@dataclass(slots=True)
class ArtifactValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)


def validate_html_artifact(html_artifact: str) -> ArtifactValidationResult:
    html = html_artifact.strip()
    errors: list[str] = []

    if not html:
        errors.append("artifact is empty")
    if "<html" not in html.lower():
        errors.append("artifact is missing an html root")
    if "</html>" not in html.lower():
        errors.append("artifact is missing a closing html tag")
    if not WINDOW_TOOL_RE.search(html):
        errors.append("artifact is missing a global window.Tool object")
    if not METADATA_RE.search(html):
        errors.append("artifact is missing Tool.metadata")
    if not DEFAULT_CONFIG_RE.search(html):
        errors.append("artifact is missing Tool.defaultConfig")
    if not TRANSFORM_RE.search(html):
        errors.append("artifact is missing Tool.transform()")
    if not INPUT_TYPE_RE.search(html):
        errors.append("artifact metadata is missing input_type")
    if not OUTPUT_TYPE_RE.search(html):
        errors.append("artifact metadata is missing output_type")

    return ArtifactValidationResult(is_valid=not errors, errors=errors)
