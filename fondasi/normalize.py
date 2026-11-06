"""Text normalization used only for evidence matching."""

from __future__ import annotations

import re

_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff"), None)

_QUOTE_MAP = str.maketrans(
    {
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u201f": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
    }
)

_WHITESPACE = re.compile(r"\s+")


def normalize_for_match(s: str) -> str:
    """Normalize text so whitespace, case, and quote style do not matter."""
    s = s.translate(_ZERO_WIDTH)
    s = s.translate(_QUOTE_MAP)
    s = s.lower()
    s = _WHITESPACE.sub(" ", s)
    return s.strip()


def is_quote_in_source(quote: str, source: str, min_words: int = 6) -> bool:
    """Return True only when the quote is long enough and literally present.

    Quotes shorter than ``min_words`` are rejected to avoid trivial matches
    such as "the property".
    """
    if len(quote.split()) < min_words:
        return False
    return normalize_for_match(quote) in normalize_for_match(source)
