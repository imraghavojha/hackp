from __future__ import annotations

import json
import ssl
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import certifi

from ai.config import AiSettings
from ai.openai_compatible import OpenAICompatibleError, _extract_json_object


@dataclass(frozen=True)
class GeminiChatResult:
    raw_text: str
    parsed_json: dict


class GeminiClient:
    def __init__(self, settings: AiSettings):
        self.settings = settings
        self._ssl_context = ssl.create_default_context(cafile=certifi.where())

    def chat_json(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.1, max_tokens: int = 2_000) -> GeminiChatResult:
        if not self.settings.live_enabled:
            raise OpenAICompatibleError("Live Gemini is not configured")

        prompt = (
            "Follow the instruction below and return JSON only.\n\n"
            f"Instruction:\n{system_prompt}\n\n"
            f"Request:\n{user_prompt}"
        )

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        request = Request(
            f"{self.settings.base_url}/models/{self.settings.model}:generateContent",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": str(self.settings.api_key),
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.settings.timeout_seconds, context=self._ssl_context) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise OpenAICompatibleError(str(exc)) from exc

        try:
            parts = body["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError, TypeError) as exc:
            raise OpenAICompatibleError("Gemini response was missing candidates[0].content.parts") from exc

        text = "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))
        return GeminiChatResult(raw_text=text, parsed_json=_extract_json_object(text))
