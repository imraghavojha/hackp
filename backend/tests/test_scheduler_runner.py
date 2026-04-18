from __future__ import annotations

import asyncio
import unittest

from backend.app.scheduler.runner import SchedulerRunner


class _FakeRepository:
    def list_user_ids(self) -> list[str]:
        return ["bob", "maya"]


class _FakeScheduler:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def maybe_process_user(self, user_id: str) -> None:
        self.calls.append(user_id)


class SchedulerRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_runner_processes_known_users(self) -> None:
        repository = _FakeRepository()
        scheduler = _FakeScheduler()
        runner = SchedulerRunner(repository=repository, scheduler=scheduler, interval_seconds=1)
        task = asyncio.create_task(runner.run_forever())
        try:
            await asyncio.sleep(0.15)
            self.assertIn("bob", scheduler.calls)
            self.assertIn("maya", scheduler.calls)
        finally:
            await runner.shutdown()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
