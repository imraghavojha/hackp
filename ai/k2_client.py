from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

from ai.config import AiSettings
from ai.openai_compatible import OpenAICompatibleError, _extract_json_object


@dataclass(frozen=True)
class K2ChatResult:
    raw_text: str
    parsed_json: dict


class K2Client:
    def __init__(self, settings: AiSettings):
        self.settings = settings

    def chat_json(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.1, max_tokens: int = 2_000) -> K2ChatResult:
        if not self.settings.live_enabled:
            raise OpenAICompatibleError("Live K2 is not configured")

        payload = {
            "model": self.settings.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            "stream": False,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        body = self._run_curl(payload)

        try:
            text = str(body["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise OpenAICompatibleError("K2 response was missing choices[0].message.content") from exc

        cleaned = text.replace("</think>", "").strip()
        try:
            parsed = _extract_json_object(cleaned)
        except OpenAICompatibleError:
            retry_payload = {
                "model": self.settings.model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt + "\nReturn exactly one JSON object. No markdown. No prose. No reasoning.",
                    },
                    {
                        "role": "user",
                        "content": user_prompt + "\nOnly output a single JSON object.",
                    },
                ],
                "stream": False,
                "temperature": 0.0,
                "max_tokens": max_tokens,
            }
            retry_body = self._run_curl(retry_payload)
            try:
                retry_text = str(retry_body["choices"][0]["message"]["content"])
            except (KeyError, IndexError, TypeError) as exc:
                raise OpenAICompatibleError("K2 retry response was missing choices[0].message.content") from exc
            cleaned = retry_text.replace("</think>", "").strip()
            parsed = _extract_json_object(cleaned)

        return K2ChatResult(raw_text=cleaned, parsed_json=parsed)

    def _run_curl(self, payload: dict) -> dict:
        command = [
            "curl",
            "-sS",
            self.settings.base_url.rstrip("/") + "/chat/completions",
            "-H",
            "accept: application/json",
            "-H",
            f"Authorization: Bearer {self.settings.api_key}",
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps(payload),
        ]

        result = subprocess.run(command, capture_output=True, text=True, timeout=self.settings.timeout_seconds, check=False)
        if result.returncode != 0:
            raise OpenAICompatibleError(result.stderr.strip() or "K2 curl request failed")

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise OpenAICompatibleError("K2 response was not valid JSON") from exc
