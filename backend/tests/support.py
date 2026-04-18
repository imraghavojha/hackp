from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


class ServiceStack:
    def __init__(self, root: Path, *, start_ai: bool = True):
        self.root = root
        self.start_ai = start_ai
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ai_process: subprocess.Popen[str] | None = None
        self.backend_process: subprocess.Popen[str] | None = None
        self.ai_port = 18011
        self.backend_port = 18010

    def __enter__(self) -> "ServiceStack":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

    def start(self) -> None:
        tmp_path = Path(self.temp_dir.name)
        backend_env = os.environ.copy()
        backend_env["PWA_DB_PATH"] = str(tmp_path / "platform.sqlite3")
        backend_env["PWA_ARTIFACTS_DIR"] = str(tmp_path / "artifacts")
        backend_env["PWA_SEED_TOOLS_PATH"] = str((self.root / "fixtures/seed/tool_registry.json").resolve())
        backend_env["PWA_RUNTIME_TEMPLATE_PATH"] = str((self.root / "runtime/shell/tool_template.html").resolve())
        backend_env["PWA_AI_BASE_URL"] = f"http://127.0.0.1:{self.ai_port}" if self.start_ai else "http://127.0.0.1:19999"
        backend_env["PWA_SCHEDULER_INTERVAL_SECONDS"] = "2"

        if self.start_ai:
            self.ai_process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "ai.app:app", "--host", "127.0.0.1", "--port", str(self.ai_port)],
                cwd=self.root,
                env=os.environ.copy(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            self._wait_for_health(f"http://127.0.0.1:{self.ai_port}/health")

        self.backend_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", str(self.backend_port)],
            cwd=self.root,
            env=backend_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        self._wait_for_health(f"http://127.0.0.1:{self.backend_port}/health")

    def stop(self) -> None:
        for process in [self.backend_process, self.ai_process]:
            if process is None:
                continue
            process.terminate()
            process.wait(timeout=5)
        self.temp_dir.cleanup()

    def get_json(self, path: str) -> dict | list:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.backend_port}{path}", timeout=10) as response:
            return json.loads(response.read().decode())

    def get_html(self, path: str) -> str:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.backend_port}{path}", timeout=10) as response:
            return response.read().decode()

    def post_json(self, path: str, payload: dict, *, expect_error: bool = False) -> dict:
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.backend_port}{path}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            if not expect_error:
                raise
            body = json.loads(exc.read().decode())
            return {"status_code": exc.code, "body": body}

    def _wait_for_health(self, url: str) -> None:
        for _ in range(40):
            try:
                with urllib.request.urlopen(url, timeout=1) as response:
                    if response.status == 200:
                        return
            except Exception:
                time.sleep(0.25)
        raise RuntimeError(f"Service failed to start: {url}")
