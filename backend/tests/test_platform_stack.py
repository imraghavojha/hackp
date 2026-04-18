from __future__ import annotations

import json
import urllib.parse
import unittest
from pathlib import Path

from backend.tests.support import ServiceStack


ROOT = Path(__file__).resolve().parents[2]


def build_events(total: int, *, url: str = "https://portal.example.com/leads", user_id: str = "bob") -> list[dict]:
    events = []
    for idx in range(total):
        events.append(
            {
                "session_id": "sess_test_stack",
                "user_id": user_id,
                "timestamp": f"2026-04-18T09:{idx % 60:02d}:00Z",
                "url": url,
                "event_type": "copy" if idx % 2 == 0 else "file_download",
                "target": {"tag": "td", "role": None, "text": f"Company {idx}", "aria_label": None},
                "value": f"Company {idx},Fintech,Series B,{100 + idx},example{idx}.com",
                "metadata": {"viewport": [1440, 900]},
            }
        )
    return events


class PlatformStackTests(unittest.TestCase):
    def test_seed_tools_exist_for_all_three_domains_and_use_light_theme(self) -> None:
        with ServiceStack(ROOT, start_ai=False) as stack:
            bob_query = urllib.parse.urlencode({"url": "https://portal.example.com/leads", "user_id": "bob"})
            maya_query = urllib.parse.urlencode({"url": "https://research.example.com/tickers", "user_id": "maya"})
            kai_query = urllib.parse.urlencode({"url": "https://support.example.com/tickets/123", "user_id": "kai"})

            bob_tools = stack.get_json(f"/v1/tools/for_url?{bob_query}")["tools"]
            maya_tools = stack.get_json(f"/v1/tools/for_url?{maya_query}")["tools"]
            kai_tools = stack.get_json(f"/v1/tools/for_url?{kai_query}")["tools"]

            self.assertEqual({tool["id"] for tool in bob_tools}, {"tool_lead_formatter_v1"})
            self.assertEqual({tool["id"] for tool in maya_tools}, {"tool_market_brief_builder_v1"})
            self.assertEqual({tool["id"] for tool in kai_tools}, {"tool_reply_drafter_v1"})
            self.assertEqual(bob_tools[0]["ui_prefs"]["theme"], "light")
            self.assertEqual(maya_tools[0]["ui_prefs"]["theme"], "light")
            self.assertEqual(kai_tools[0]["ui_prefs"]["theme"], "light")

    def test_seed_tool_survives_when_ai_is_unavailable(self) -> None:
        with ServiceStack(ROOT, start_ai=False) as stack:
            accepted = stack.post_json("/v1/events", {"user_id": "bob", "events": build_events(50)})
            self.assertEqual(accepted["accepted"], 50)

            query = urllib.parse.urlencode({"url": "https://portal.example.com/leads", "user_id": "bob"})
            tools = stack.get_json(f"/v1/tools/for_url?{query}")["tools"]
            tool_ids = {tool["id"] for tool in tools}
            self.assertIn("tool_lead_formatter_v1", tool_ids)
            self.assertNotIn("tool_domain_a_lead_formatter_v1", tool_ids)

    def test_event_batch_generates_corporate_domain_a_tool(self) -> None:
        with ServiceStack(ROOT, start_ai=True) as stack:
            accepted = stack.post_json("/v1/events", {"user_id": "bob", "events": build_events(50)})
            self.assertEqual(accepted["accepted"], 50)

            query = urllib.parse.urlencode({"url": "https://portal.example.com/leads", "user_id": "bob"})
            tools = stack.get_json(f"/v1/tools/for_url?{query}")["tools"]
            tool_ids = {tool["id"] for tool in tools}
            self.assertIn("tool_domain_a_lead_formatter_v1", tool_ids)
            generated = [tool for tool in tools if tool["id"] == "tool_domain_a_lead_formatter_v1"][0]
            self.assertEqual(generated["ui_prefs"]["theme"], "light")

            generated_html = stack.get_html("/v1/tools/tool_domain_a_lead_formatter_v1/artifact")
            self.assertIn("window.Tool", generated_html)
            self.assertIn('data-theme="light"', generated_html)

    def test_domain_b_and_c_cached_tools_run_through_orchestrator(self) -> None:
        with ServiceStack(ROOT, start_ai=False) as stack:
            market = stack.post_json(
                "/internal/orchestrator/run_tool",
                {
                    "tool_id": "tool_market_brief_builder_v1",
                    "user_id": "maya",
                    "input_data": json.dumps(
                        {
                            "tickers": ["AAPL", "MSFT"],
                            "market_data": {
                                "AAPL": {"price": 194.11, "market_cap": "3.0T"},
                                "MSFT": {"price": 421.88, "market_cap": "3.1T"},
                            },
                        }
                    ),
                },
            )
            reply = stack.post_json(
                "/internal/orchestrator/run_tool",
                {
                    "tool_id": "tool_reply_drafter_v1",
                    "user_id": "kai",
                    "input_data": json.dumps(
                        {
                            "ticket": {"ticket_id": "TICK-1024", "subject": "Refund request"},
                            "customer": {"name": "Jordan Lee", "plan": "enterprise"},
                        }
                    ),
                },
            )
            self.assertTrue(market["succeeded"])
            self.assertEqual(len(market["output_preview"]["preview_output"]), 3)
            self.assertTrue(reply["succeeded"])
            self.assertIn("Jordan Lee", reply["output_preview"]["preview_output"][1][0])

    def test_internal_artifact_endpoint_rejects_invalid_html(self) -> None:
        with ServiceStack(ROOT, start_ai=False) as stack:
            response = stack.post_json(
                "/internal/artifacts",
                {"user_id": "bob", "html_artifact": "<html>bad</html>"},
                expect_error=True,
            )
            self.assertEqual(response["status_code"], 422)
            self.assertTrue(response["body"]["detail"]["errors"])
