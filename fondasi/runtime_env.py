"""Mirror Streamlit Cloud secrets into environment variables.

Streamlit stores secrets in ``st.secrets``, while the provider classes read
``os.environ``. Without this bridge a key added in the Streamlit dashboard is
invisible to the app. Only known names are copied, real environment variables
win, and no value is ever logged.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, MutableMapping

SECRET_KEYS = (
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_MODEL",
    "COMMANDCODE_API_KEY",
    "COMMANDCODE_MODEL",
    "FONDASI_MAX_SOURCE_WORDS",
    "FONDASI_TEMPERATURE",
)


def mirror_secrets(
    secrets: Mapping[str, object],
    environ: MutableMapping[str, str] | None = None,
) -> list[str]:
    """Copy known secret names into the environment and return the names copied."""
    target = environ if environ is not None else os.environ
    copied: list[str] = []
    for key in SECRET_KEYS:
        try:
            value = secrets.get(key)
        except Exception:
            continue
        if value is None or value == "":
            continue
        if target.get(key):
            continue
        target[key] = str(value)
        copied.append(key)
    return copied
