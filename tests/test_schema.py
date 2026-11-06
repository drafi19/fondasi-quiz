import pytest
from pydantic import ValidationError

from fondasi.schema import QuestionType, QuizItem


def make_item(**overrides):
    data = {
        "id": "item-1",
        "type": QuestionType.mcq,
        "prompt": "What is the duration?",
        "options": ["One week", "Two weeks", "Three weeks", "Four weeks"],
        "correct_index": 2,
        "explanation": "The source says three weeks.",
        "evidence_quote": "The onboarding program lasts three weeks.",
    }
    data.update(overrides)
    return QuizItem(**data)


def test_mcq_with_three_options_fails():
    with pytest.raises(ValidationError):
        make_item(options=["One week", "Two weeks", "Three weeks"])


def test_mcq_correct_index_four_fails():
    with pytest.raises(ValidationError):
        make_item(correct_index=4)


def test_short_answer_without_accepted_answers_fails():
    with pytest.raises(ValidationError):
        make_item(
            type=QuestionType.short_answer,
            options=[],
            correct_index=None,
            accepted_answers=[],
        )


def test_mcq_with_duplicate_options_fails():
    with pytest.raises(ValidationError):
        make_item(options=["Three weeks", "Three weeks", "Two weeks", "One week"])


def test_true_false_requires_exact_options():
    with pytest.raises(ValidationError):
        make_item(
            type=QuestionType.true_false,
            options=["Yes", "No"],
            correct_index=0,
        )


def test_valid_short_answer_passes():
    item = make_item(
        type=QuestionType.short_answer,
        options=[],
        correct_index=None,
        accepted_answers=["three weeks"],
    )
    assert item.accepted_answers == ["three weeks"]
