from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from ai.client import detect_transformation, generate_tool
from ai.config import get_ai_settings
from ai.mem0_wrapper.client import build_preferences_block
from ai.openai_compatible import OpenAICompatibleClient


ROOT = Path(__file__).resolve().parents[2]


def sample_events(url: str = "https://portal.example.com/leads") -> list[dict]:
    return [
        {
            "session_id": "sess_ai_1",
            "user_id": "bob",
            "timestamp": "2026-04-18T09:01:00Z",
            "url": url,
            "event_type": "copy",
            "target": {"tag": "td", "role": None, "text": "Acme", "aria_label": None},
            "value": "Acme,Fintech,Series B,120,acme.com",
            "metadata": {},
        },
        {
            "session_id": "sess_ai_1",
            "user_id": "bob",
            "timestamp": "2026-04-18T09:03:00Z",
            "url": url,
            "event_type": "file_download",
            "target": {"tag": "button", "role": "button", "text": "Export CSV", "aria_label": None},
            "value": "leads.csv",
            "metadata": {},
        },
    ]


class _ChatHandler(BaseHTTPRequestHandler):
    response_payload: dict = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "detected": True,
                            "confidence": 0.91,
                            "summary": "Live test summary",
                            "input_characterization": "csv",
                            "output_characterization": "xlsx",
                            "repetition_count": 3,
                        }
                    )
                }
            }
        ]
    }

    def do_POST(self):  # noqa: N802
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self.server.requests.append(json.loads(body.decode("utf-8")))
        encoded = json.dumps(self.response_payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):  # noqa: A003
        return


class AiIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        get_ai_settings.cache_clear()

    def tearDown(self) -> None:
        get_ai_settings.cache_clear()

    def test_settings_load_from_standard_env_shape(self) -> None:
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-key",
                "OPENAI_BASE_URL": "http://127.0.0.1:9999/v1",
                "OPENAI_MODEL": "gpt-4.1-mini",
                "PWA_AI_MODE": "hybrid",
            },
            clear=False,
        ):
            get_ai_settings.cache_clear()
            settings = get_ai_settings()
            self.assertEqual(settings.api_key, "test-key")
            self.assertEqual(settings.base_url, "http://127.0.0.1:9999/v1")
            self.assertEqual(settings.model, "gpt-4.1-mini")
            self.assertTrue(settings.live_enabled)

    def test_preferences_block_prefers_corporate_defaults(self) -> None:
        with patch.dict(os.environ, {"PWA_MEM0_MODE": "local"}, clear=False):
            get_ai_settings.cache_clear()
            block = build_preferences_block("bob", "[ui] initials=BK\n[ui] theme=light")
            self.assertIn("theme=light", block)
            self.assertIn("enterprise-friendly", block)
            self.assertIn("initials=BK", block)

    def test_detect_transformation_supports_all_demo_domains(self) -> None:
        domain_b = detect_transformation({"user_id": "maya", "events": sample_events("https://research.example.com/tickers"), "existing_tool_signatures": []})
        domain_c = detect_transformation({"user_id": "kai", "events": sample_events("https://support.example.com/tickets/123"), "existing_tool_signatures": []})
        self.assertEqual(domain_b["signature"], "sig_domain_b_market_brief")
        self.assertEqual(domain_c["signature"], "sig_domain_c_reply_drafter")

    def test_generate_tool_fallback_returns_corporate_domain_a_artifact(self) -> None:
        detection = detect_transformation({"user_id": "bob", "events": sample_events(), "existing_tool_signatures": []})
        generated = generate_tool(
            {
                "user_id": "bob",
                "detection": detection,
                "events": sample_events(),
                "user_prefs_hint": "theme=light\ninitials=BO",
            }
        )
        self.assertEqual(generated["ui_prefs"]["theme"], "light")
        self.assertIn("window.Tool", generated["html_artifact"])
        self.assertIn("Lead List Formatter", generated["html_artifact"])
        self.assertIn("BO", generated["html_artifact"])

    def test_openai_compatible_client_parses_json_from_stub_server(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), _ChatHandler)
        server.requests = []
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "test-key",
                    "OPENAI_BASE_URL": f"http://127.0.0.1:{server.server_port}/v1",
                    "OPENAI_MODEL": "gpt-4.1-mini",
                    "PWA_AI_MODE": "live",
                },
                clear=False,
            ):
                get_ai_settings.cache_clear()
                client = OpenAICompatibleClient(get_ai_settings())
                result = client.chat_json(system_prompt="system", user_prompt="user")
                self.assertTrue(result.parsed_json["detected"])
                self.assertEqual(len(server.requests), 1)
                self.assertEqual(server.requests[0]["model"], "gpt-4.1-mini")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
