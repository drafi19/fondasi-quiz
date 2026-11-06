"""Provider factory."""

from __future__ import annotations

from fondasi.providers.base import Provider, ProviderError
from fondasi.providers.commandcode import CommandCodeProvider
from fondasi.providers.fake import FakeProvider
from fondasi.providers.gemini import GeminiProvider
from fondasi.providers.openrouter import OpenRouterProvider


def get_provider(name: str, model: str | None = None) -> Provider:
    """Return a provider by name, raising a clear error for unknown names.

    ``model`` overrides the environment default so the model shown in the UI is
    the model that actually answers the request.
    """
    key = name.strip().lower()
    if key == "gemini":
        return GeminiProvider(model=model)
    if key == "openrouter":
        return OpenRouterProvider(model=model)
    if key == "commandcode":
        return CommandCodeProvider(model=model)
    raise ProviderError(f"Unknown provider: {name}")


def provider_model(name: str) -> str:
    """Return the configured model label for display and export."""
    from fondasi.config import commandcode_model, gemini_model, openrouter_model

    key = name.strip().lower()
    if key == "gemini":
        return gemini_model()
    if key == "openrouter":
        return openrouter_model()
    if key == "commandcode":
        return commandcode_model()
    return "fake"


__all__ = [
    "CommandCodeProvider",
    "FakeProvider",
    "GeminiProvider",
    "OpenRouterProvider",
    "Provider",
    "ProviderError",
    "get_provider",
    "provider_model",
]
