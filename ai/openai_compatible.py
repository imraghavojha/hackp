from __future__ import annotations

import json
import ssl
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import certifi

from ai.config import AiSettings


class OpenAICompatibleError(RuntimeError):
    pass


@dataclass(frozen=True)
class OpenAIChatResult:
    raw_text: str
    parsed_json: dict


def _extract_json_object(text: str) -> dict:
    cleaned = text.strip().replace("```json", "").replace("```", "").strip()
    if "</think>" in cleaned:
        cleaned = cleaned.rsplit("</think>", maxsplit=1)[-1].strip()
    else:
        cleaned = cleaned.replace("</think>", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    search_from = 0
    while True:
        start = cleaned.find("{", search_from)
        if start == -1:
            break

        try:
            candidate, _ = decoder.raw_decode(cleaned[start:])
        except json.JSONDecodeError:
            search_from = start + 1
            continue

        if isinstance(candidate, dict):
            return candidate
        search_from = start + 1

    raise OpenAICompatibleError("Model response did not contain a valid JSON object")


class OpenAICompatibleClient:
    def __init__(self, settings: AiSettings):
        self.settings = settings
        self._ssl_context = ssl.create_default_context(cafile=certifi.where())

    def chat_json(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.1, max_tokens: int = 2_000) -> OpenAIChatResult:
        if not self.settings.live_enabled:
            raise OpenAICompatibleError("Live AI is not configured")

        payload = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        request = Request(
            f"{self.settings.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.api_key}",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.settings.timeout_seconds, context=self._ssl_context) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise OpenAICompatibleError(str(exc)) from exc

        try:
            message = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise OpenAICompatibleError("OpenAI-compatible response was missing choices[0].message.content") from exc

        if isinstance(message, list):
            text = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in message
            )
        else:
            text = str(message)

        return OpenAIChatResult(raw_text=text, parsed_json=_extract_json_object(text))
