from __future__ import annotations

from datetime import datetime
import unittest
from zoneinfo import ZoneInfo

from backend.app.artifacts.validator import validate_html_artifact
from backend.app.contracts import ToolTrigger
from backend.app.triggers.url_visit import matches_tool_trigger


class PlatformUnitTests(unittest.TestCase):
    def test_validator_accepts_json_quoted_metadata_keys(self) -> None:
        html = """
        <!DOCTYPE html>
        <html>
          <body>
            <script>
              const meta = {"input_type":"json","output_type":"text"};
              window.Tool = {
                metadata: meta,
                defaultConfig: {},
                async transform(input) { return input; }
              };
            </script>
          </body>
        </html>
        """
        result = validate_html_artifact(html)
        self.assertTrue(result.is_valid)

    def test_validator_rejects_missing_contract_shape(self) -> None:
        result = validate_html_artifact("<html><body><script>const nope = true;</script></body></html>")
        self.assertFalse(result.is_valid)
        self.assertTrue(result.errors)

    def test_trigger_matching_respects_time_windows(self) -> None:
        trigger = ToolTrigger.model_validate(
            {
                "type": "on_url_visit",
                "url_pattern": "portal.example.com/leads",
                "prompt": "x",
                "time_window": {"start": "08:00", "end": "10:30", "timezone": "America/New_York"},
            }
        )
        inside = datetime(2026, 4, 18, 9, 0, tzinfo=ZoneInfo("America/New_York"))
        outside = datetime(2026, 4, 18, 12, 0, tzinfo=ZoneInfo("America/New_York"))
        self.assertTrue(matches_tool_trigger(trigger, "https://portal.example.com/leads", now=inside))
        self.assertFalse(matches_tool_trigger(trigger, "https://portal.example.com/leads", now=outside))
