"""Provider interface shared by every model backend."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ProviderError(Exception):
    """A provider failed. ``transient`` controls whether the pipeline retries."""

    def __init__(self, message: str, transient: bool = False) -> None:
        super().__init__(message)
        self.transient = transient


# 429 is a rate limit, not a permanent error: a free tier answers with it after
# five requests in a minute, and the run should wait rather than die.
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class Provider(ABC):
    name: str

    @abstractmethod
    def generate_json(self, system: str, user: str, schema_hint: str) -> dict:
        """Return a parsed JSON object from the model."""
        raise NotImplementedError
