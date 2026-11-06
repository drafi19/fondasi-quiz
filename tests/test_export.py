import csv
import io

from fondasi.export import CSV_HEADER, to_csv, to_json, to_markdown
from fondasi.schema import QuestionType, Quiz, QuizItem


def make_quiz() -> Quiz:
    items = [
        QuizItem(
            id="1",
            type=QuestionType.mcq,
            prompt="How long does the program last?",
            options=["One week", "Two weeks", "Three weeks", "Six weeks"],
            correct_index=2,
            explanation="The source says three weeks.",
            evidence_quote="The onboarding program lasts three weeks.",
        ),
        QuizItem(
            id="2",
            type=QuestionType.short_answer,
            prompt="Who mentors each new agent?",
            accepted_answers=["a senior mentor", "senior mentor"],
            explanation="The quote names a senior mentor.",
            evidence_quote="Each new agent is paired with a senior mentor.",
        ),
    ]
    return Quiz(
        topic="Onboarding",
        source_title="Onboarding notes",
        source_url="https://example.com/notes",
        language="source",
        items=items,
        model="fake",
    )


def test_markdown_contains_answer_key():
    markdown = to_markdown(make_quiz())
    assert "## Answer key" in markdown
    assert "Evidence:" in markdown


def test_csv_has_expected_header():
    rows = list(csv.reader(io.StringIO(to_csv(make_quiz()))))
    assert rows[0] == CSV_HEADER
    assert len(rows) == 3


def test_json_round_trips_through_model():
    quiz = make_quiz()
    restored = Quiz.model_validate_json(to_json(quiz))
    assert restored == quiz
