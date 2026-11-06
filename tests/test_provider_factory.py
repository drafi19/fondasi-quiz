"""The provider factory must pass a model override through to the client."""

from __future__ import annotations

import pytest

from fondasi.providers import get_provider
from fondasi.providers.base import ProviderError


def test_model_override_reaches_the_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMMANDCODE_API_KEY", "dummy-key")
    provider = get_provider("commandcode", model="deepseek/test-model")
    assert provider.model == "deepseek/test-model"


def test_default_model_is_used_when_no_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMMANDCODE_API_KEY", "dummy-key")
    monkeypatch.setenv("COMMANDCODE_MODEL", "deepseek/from-env")
    provider = get_provider("commandcode")
    assert provider.model == "deepseek/from-env"


def test_unknown_provider_name_raises() -> None:
    with pytest.raises(ProviderError):
        get_provider("not-a-provider")
