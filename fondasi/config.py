"""Runtime configuration read from environment variables.

No secrets are ever stored in files. Only variable names appear in
``.env.example`` and in the error messages raised by provider factories.
"""

from __future__ import annotations

import os

DEFAULT_MAX_SOURCE_WORDS = 6000
DEFAULT_TEMPERATURE = 0.2

GEMINI_DEFAULT_MODEL = "gemini-2.5-flash"


def max_source_words() -> int:
    """Return the configured source word cap."""
    raw = os.getenv("FONDASI_MAX_SOURCE_WORDS", str(DEFAULT_MAX_SOURCE_WORDS))
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_SOURCE_WORDS
    return value if value > 0 else DEFAULT_MAX_SOURCE_WORDS


def temperature() -> float:
    """Return the configured sampling temperature."""
    raw = os.getenv("FONDASI_TEMPERATURE", str(DEFAULT_TEMPERATURE))
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_TEMPERATURE


def gemini_model() -> str:
    return os.getenv("GEMINI_MODEL") or GEMINI_DEFAULT_MODEL


def openrouter_model() -> str:
    return os.getenv("OPENROUTER_MODEL") or "openai/gpt-4o-mini"


def commandcode_model() -> str:
    return os.getenv("COMMANDCODE_MODEL") or "deepseek/deepseek-v4.1-flash-fast"
