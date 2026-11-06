"""A deterministic provider used by tests and the offline demo."""

from __future__ import annotations

from fondasi.providers.base import Provider, ProviderError


class FakeProvider(Provider):
    name = "fake"

    def __init__(self, responses: list[dict]) -> None:
        self._responses = list(responses)
        self._index = 0

    @property
    def remaining(self) -> int:
        return len(self._responses) - self._index

    def generate_json(self, system: str, user: str, schema_hint: str) -> dict:
        if self._index >= len(self._responses):
            raise ProviderError("FakeProvider ran out of scripted responses.")
        response = self._responses[self._index]
        self._index += 1
        return response
