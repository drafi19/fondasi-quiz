"""Google Gemini REST provider."""

from __future__ import annotations

import json
import os

import httpx

from fondasi.config import gemini_model, temperature
from fondasi.providers.base import RETRYABLE_STATUS, Provider, ProviderError

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiProvider(Provider):
    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ProviderError(
                "GEMINI_API_KEY is not set. Add it to your environment or .env file."
            )
        self.model = model or gemini_model()

    def generate_json(self, system: str, user: str, schema_hint: str) -> dict:
        url = ENDPOINT.format(model=self.model)
        body = {
            "systemInstruction": {
                "parts": [{"text": f"{system}\n\nOutput schema:\n{schema_hint}"}]
            },
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": temperature(),
            },
        }
        try:
            response = httpx.post(
                url,
                params={"key": self.api_key},
                json=body,
                timeout=90.0,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            detail = " ".join(exc.response.text.split())[:300]
            detail = detail.replace(self.api_key, "***")
            raise ProviderError(
                f"Gemini request failed with status {status}: {detail}",
                transient=status in RETRYABLE_STATUS,
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderError(
                f"Gemini request failed: {type(exc).__name__}",
                transient=True,
            ) from exc

        try:
            payload = response.json()
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError(f"Gemini returned an unusable response: {exc}") from exc
