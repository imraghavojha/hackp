from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.artifacts.store import ArtifactStore
from backend.app.config import Settings
from backend.app.orchestrator.service import ToolOrchestrator
from backend.app.registry.tools import ToolRegistry
from backend.app.routes.internal.artifacts import router as artifacts_router
from backend.app.routes.internal.orchestrator import router as orchestrator_router
from backend.app.routes.v1.events import router as events_router
from backend.app.routes.v1.feedback import router as feedback_router
from backend.app.routes.v1.tools import router as tools_router
from backend.app.scheduler.detect_loop import DetectionScheduler, HttpAiGateway
from backend.app.scheduler.runner import SchedulerRunner, stop_scheduler_task
from backend.app.store.db import Database
from backend.app.store.repository import PlatformRepository


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    database = Database(settings.db_path)
    database.initialize()
    repository = PlatformRepository(database)
    artifact_store = ArtifactStore(settings.artifacts_dir)
    registry = ToolRegistry(repository=repository, artifact_store=artifact_store, settings=settings)
    registry.ensure_seed_data()
    orchestrator = ToolOrchestrator(repository=repository, artifact_store=artifact_store)
    scheduler = DetectionScheduler(
        repository=repository,
        artifact_store=artifact_store,
        ai_gateway=HttpAiGateway(settings.ai_base_url),
    )
    scheduler_runner = SchedulerRunner(
        repository=repository,
        scheduler=scheduler,
        interval_seconds=settings.scheduler_interval_seconds,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        task: asyncio.Task[None] | None = None
        if settings.scheduler_enabled:
            task = asyncio.create_task(scheduler_runner.run_forever(), name="pwa-scheduler-runner")
        try:
            yield
        finally:
            if task is not None:
                await stop_scheduler_task(task, scheduler_runner)

    app = FastAPI(title="Personal Workflow Agent Backend", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.repository = repository
    app.state.artifact_store = artifact_store
    app.state.registry = registry
    app.state.orchestrator = orchestrator
    app.state.scheduler = scheduler
    app.state.scheduler_runner = scheduler_runner

    app.include_router(events_router)
    app.include_router(tools_router)
    app.include_router(feedback_router)
    app.include_router(artifacts_router)
    app.include_router(orchestrator_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
