from __future__ import annotations

from fastapi import FastAPI

from ai.client import detect_transformation, generate_tool
from ai.contracts import DetectionRequest, DetectionResponse, GenerateToolRequest, GenerateToolResponse


def create_app() -> FastAPI:
    app = FastAPI(title="Personal Workflow Agent AI Service", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/ai/detect_transformation", response_model=DetectionResponse)
    def detect(payload: DetectionRequest) -> DetectionResponse:
        return DetectionResponse.model_validate(detect_transformation(payload.model_dump(mode="json")))

    @app.post("/ai/generate_tool", response_model=GenerateToolResponse)
    def generate(payload: GenerateToolRequest) -> GenerateToolResponse:
        return GenerateToolResponse.model_validate(generate_tool(payload.model_dump(mode="json")))

    return app


app = create_app()
