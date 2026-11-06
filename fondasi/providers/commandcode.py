"""CommandCode provider using its OpenAI-compatible chat endpoint."""

from __future__ import annotations

import json
import os

import httpx

from fondasi.config import commandcode_model, temperature
from fondasi.providers.base import Provider, ProviderError

ENDPOINT = "https://api.commandcode.ai/provider/v1/chat/completions"


class CommandCodeProvider(Provider):
    name = "commandcode"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("COMMANDCODE_API_KEY")
        if not self.api_key:
            raise ProviderError(
                "COMMANDCODE_API_KEY is not set. Add it to your environment or .env file."
            )
        self.model = model or commandcode_model()

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
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            response = httpx.post(ENDPOINT, json=body, headers=headers, timeout=60.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            transient = isinstance(exc, httpx.RequestError) or (
                isinstance(exc, httpx.HTTPStatusError)
                and exc.response.status_code >= 500
            )
            raise ProviderError(
                f"CommandCode request failed: {exc}", transient=transient
            ) from exc

        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError(f"CommandCode returned an unusable response: {exc}") from exc
