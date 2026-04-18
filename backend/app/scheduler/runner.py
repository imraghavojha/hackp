from __future__ import annotations

import asyncio
from contextlib import suppress

from backend.app.scheduler.detect_loop import DetectionScheduler
from backend.app.store.repository import PlatformRepository


class SchedulerRunner:
    def __init__(self, *, repository: PlatformRepository, scheduler: DetectionScheduler, interval_seconds: int):
        self.repository = repository
        self.scheduler = scheduler
        self.interval_seconds = interval_seconds
        self._stop = asyncio.Event()

    async def run_forever(self) -> None:
        while not self._stop.is_set():
            user_ids = self.repository.list_user_ids()
            for user_id in user_ids:
                await asyncio.to_thread(self.scheduler.maybe_process_user, user_id)

            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                continue

    async def shutdown(self) -> None:
        self._stop.set()


async def stop_scheduler_task(task: asyncio.Task[None], runner: SchedulerRunner) -> None:
    await runner.shutdown()
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
