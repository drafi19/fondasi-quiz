from fondasi.pipeline import QuizPipeline
from fondasi.providers.fake import FakeProvider
from fondasi.schema import QuestionType, Quiz, QuizItem, SourceDoc

SOURCE = (
    "The onboarding program lasts three weeks and begins every Monday. "
    "Each new agent is paired with a senior mentor."
)


def make_doc() -> SourceDoc:
    return SourceDoc(title="Onboarding", text=SOURCE, char_count=len(SOURCE))


def make_item(item_id: str, prompt: str, quote: str) -> QuizItem:
    return QuizItem(
        id=item_id,
        type=QuestionType.true_false,
        prompt=prompt,
        options=["True", "False"],
        correct_index=0,
        explanation="The quote supports the claim.",
        evidence_quote=quote,
        source_section=None,
    )


def make_quiz(items: list[QuizItem]) -> Quiz:
    return Quiz(
        topic="Onboarding",
        source_title="Onboarding",
        language="source",
        items=items,
        model="fake",
    )


def test_paraphrased_quote_is_dropped_with_reason():
    exact = make_item(
        "1",
        "The program begins every Monday.",
        "The onboarding program lasts three weeks and begins every Monday.",
    )
    paraphrased = make_item(
        "2",
        "Each agent is paired with a senior mentor.",
        "Each new hire is matched with an experienced guide.",
    )
    pipeline = QuizPipeline(FakeProvider([]), "fake")
    cleaned = pipeline.mechanical_checks(make_quiz([exact, paraphrased]), make_doc())

    assert [item.id for item in cleaned.items] == ["1"]
    assert len(cleaned.dropped) == 1
    assert "verbatim" in cleaned.dropped[0].reason.lower()


def test_exact_quote_survives():
    exact = make_item(
        "1",
        "Each new agent is paired with a senior mentor.",
        "Each new agent is paired with a senior mentor.",
    )
    pipeline = QuizPipeline(FakeProvider([]), "fake")
    cleaned = pipeline.mechanical_checks(make_quiz([exact]), make_doc())

    assert len(cleaned.items) == 1
    assert cleaned.dropped == []
