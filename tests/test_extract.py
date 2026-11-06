"""Pasted text keeps its own headline as the title."""

from __future__ import annotations

import pytest

from fondasi.extract import ExtractError, extract_from_text


def test_first_line_becomes_the_title() -> None:
    doc = extract_from_text("Siaran Pers Bank Indonesia\n\nIsi paragraf pertama.", "topik")
    assert doc.title == "Siaran Pers Bank Indonesia"


def test_long_first_line_falls_back_to_the_topic() -> None:
    body = "x" * 200 + "\n\nIsi paragraf."
    doc = extract_from_text(body, "Topik yang diketik user")
    assert doc.title == "Topik yang diketik user"


def test_empty_text_raises() -> None:
    with pytest.raises(ExtractError):
        extract_from_text("   \n  ", "topik")
