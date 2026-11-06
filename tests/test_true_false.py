"""True or false items accept an English or an Indonesian option pair."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from fondasi.schema import QuestionType, QuizItem


def _item(options: list[str], correct_index: int = 0) -> QuizItem:
    return QuizItem(
        id="item-1",
        type=QuestionType.true_false,
        prompt="Klaim yang diuji.",
        options=options,
        correct_index=correct_index,
        explanation="Penjelasan singkat.",
        evidence_quote="kutipan yang cukup panjang dari sumber",
    )


def test_english_pair_is_accepted() -> None:
    assert _item(["True", "False"]).options == ["True", "False"]


def test_indonesian_pair_is_accepted() -> None:
    assert _item(["Benar", "Salah"], correct_index=1).options == ["Benar", "Salah"]


def test_other_pairs_are_rejected() -> None:
    with pytest.raises(ValidationError):
        _item(["Ya", "Tidak"])


def test_correct_index_must_be_zero_or_one() -> None:
    with pytest.raises(ValidationError):
        _item(["True", "False"], correct_index=2)
