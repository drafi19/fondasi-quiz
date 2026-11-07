"""Provider errors must be classified without leaking the API key."""

from __future__ import annotations

import httpx
import pytest

from fondasi.providers.base import ProviderError
from fondasi.providers.gemini import GeminiProvider

KEY = "AQ.SECRET-KEY-SHOULD-NOT-LEAK"


def _raise(status: int, body: str, monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("POST", "https://example.test")
    response = httpx.Response(status, request=request, text=body)

    def boom(*args: object, **kwargs: object) -> None:
        raise httpx.HTTPStatusError("boom", request=request, response=response)

    monkeypatch.setattr(httpx, "post", boom)


def _call() -> None:
    provider = GeminiProvider(api_key=KEY, model="gemini-3.1-flash-lite")
    provider.generate_json("system", "user", "{}")


def test_rate_limit_is_transient(monkeypatch: pytest.MonkeyPatch) -> None:
    _raise(429, f"quota exceeded for key {KEY}", monkeypatch)
    with pytest.raises(ProviderError) as caught:
        _call()
    assert caught.value.transient is True
    assert "429" in str(caught.value)


def test_bad_request_is_not_transient(monkeypatch: pytest.MonkeyPatch) -> None:
    _raise(400, "invalid argument", monkeypatch)
    with pytest.raises(ProviderError) as caught:
        _call()
    assert caught.value.transient is False


def test_api_key_never_appears_in_the_message(monkeypatch: pytest.MonkeyPatch) -> None:
    _raise(429, f"quota exceeded for key {KEY}", monkeypatch)
    with pytest.raises(ProviderError) as caught:
        _call()
    assert KEY not in str(caught.value)
    assert "***" in str(caught.value)
