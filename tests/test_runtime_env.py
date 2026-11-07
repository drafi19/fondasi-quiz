"""Streamlit secrets must reach the environment variables the providers read."""

from __future__ import annotations

from fondasi.runtime_env import mirror_secrets


def test_known_keys_are_copied() -> None:
    env: dict[str, str] = {}
    copied = mirror_secrets({"GEMINI_API_KEY": "abc", "UNRELATED": "x"}, env)
    assert copied == ["GEMINI_API_KEY"]
    assert env["GEMINI_API_KEY"] == "abc"
    assert "UNRELATED" not in env


def test_existing_environment_wins() -> None:
    env = {"GEMINI_API_KEY": "from-machine"}
    copied = mirror_secrets({"GEMINI_API_KEY": "from-secret"}, env)
    assert copied == []
    assert env["GEMINI_API_KEY"] == "from-machine"


def test_empty_values_are_skipped() -> None:
    env: dict[str, str] = {}
    assert mirror_secrets({"GEMINI_API_KEY": ""}, env) == []
    assert env == {}


def test_missing_key_is_skipped() -> None:
    env: dict[str, str] = {}
    assert mirror_secrets({"GEMINI_MODEL": "gemini-3.1-flash-lite"}, env) == [
        "GEMINI_MODEL"
    ]
