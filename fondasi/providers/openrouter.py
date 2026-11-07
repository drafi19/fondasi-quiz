"""OpenRouter provider using the OpenAI-compatible chat endpoint."""

from __future__ import annotations

import json
import os

import httpx

from fondasi.config import openrouter_model, temperature
from fondasi.providers.base import RETRYABLE_STATUS, Provider, ProviderError

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterProvider(Provider):
    name = "openrouter"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ProviderError(
                "OPENROUTER_API_KEY is not set. Add it to your environment or .env file."
            )
        self.model = model or openrouter_model()

    def generate_json(self, system: str, user: str, schema_hint: str) -> dict:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": f"{system}\n\nOutput schema:\n{schema_hint}"},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": temperature(),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/",
            "X-Title": "Fondasi Quiz",
        }
        try:
            response = httpx.post(ENDPOINT, json=body, headers=headers, timeout=60.0)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"OpenRouter request failed with status {exc.response.status_code}",
                transient=exc.response.status_code in RETRYABLE_STATUS,
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderError(
                f"OpenRouter request failed: {type(exc).__name__}", transient=True
            ) from exc

        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError(f"OpenRouter returned an unusable response: {exc}") from exc
