"""
Backend composition root.

Keep this layer thin. The first concrete goal is to expose stable fixture-backed
handlers for the extension before live AI generation is wired in.
"""

PUBLIC_SURFACES = [
    "POST /v1/events",
    "GET /v1/tools/for_url",
    "GET /v1/tools/{id}/artifact",
    "POST /v1/tools/{id}/usage",
    "POST /v1/feedback",
]

INTERNAL_SURFACES = [
    "POST /internal/artifacts",
    "GET /internal/artifacts/{id}",
    "POST /internal/orchestrator/run_tool",
]
