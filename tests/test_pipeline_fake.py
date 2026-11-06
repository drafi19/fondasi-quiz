from fondasi.pipeline import QuizPipeline
from fondasi.providers.fake import FakeProvider
from fondasi.schema import QuestionType, SourceDoc

SOURCE = (
    "The onboarding program lasts three weeks and begins every Monday. "
    "Each new agent is paired with a senior mentor."
)

QUOTE_ONE = "The onboarding program lasts three weeks and begins every Monday."
QUOTE_TWO = "Each new agent is paired with a senior mentor."


def make_doc() -> SourceDoc:
    return SourceDoc(title="Onboarding", text=SOURCE, char_count=len(SOURCE))


def blueprint() -> dict:
    return {
        "facts": [
            {"statement": "The program lasts three weeks.", "quote": QUOTE_ONE, "section": ""},
            {"statement": "New agents get a senior mentor.", "quote": QUOTE_TWO, "section": ""},
        ],
        "note": "",
    }


def mcq_payload() -> dict:
    return {
        "type": "mcq",
        "prompt": "How long does the onboarding program last?",
        "options": ["One week", "Two weeks", "Three weeks", "Six weeks"],
        "correct_index": 2,
        "accepted_answers": [],
        "explanation": "The source says three weeks.",
        "evidence_quote": QUOTE_ONE,
    }


def tf_payload() -> dict:
    return {
        "type": "true_false",
        "prompt": "New agents are paired with a senior mentor.",
        "options": ["True", "False"],
        "correct_index": 0,
        "accepted_answers": [],
        "explanation": "The quote states this directly.",
        "evidence_quote": QUOTE_TWO,
    }


def pass_verdict() -> dict:
    return {
        "supported": True,
        "answer_correct": True,
        "distractors_ok": True,
        "unique_answer": True,
        "note": "Supported by the quote.",
    }


def fail_verdict() -> dict:
    return {
        "supported": False,
        "answer_correct": True,
        "distractors_ok": True,
        "unique_answer": True,
        "note": "The quote does not settle the duration.",
    }


def test_run_with_passing_verdicts_keeps_all_items():
    provider = FakeProvider(
        [
            blueprint(),
            mcq_payload(),
            pass_verdict(),
            tf_payload(),
            pass_verdict(),
        ]
    )
    pipeline = QuizPipeline(
        provider,
        "fake",
        n_items=2,
        mix={QuestionType.mcq: 1, QuestionType.true_false: 1},
    )
    quiz = pipeline.run(make_doc(), "Onboarding")

    assert len(quiz.items) == 2
    assert quiz.dropped == []
    assert quiz.items[0].type is QuestionType.mcq
    assert quiz.items[1].type is QuestionType.true_false


def test_run_drops_item_after_failed_repair_and_second_verification():
    provider = FakeProvider(
        [
            {"facts": [{"statement": "The program lasts three weeks.", "quote": QUOTE_ONE}]},
            mcq_payload(),
            fail_verdict(),
            mcq_payload(),
            fail_verdict(),
        ]
    )
    pipeline = QuizPipeline(
        provider,
        "fake",
        n_items=1,
        mix={QuestionType.mcq: 1},
    )
    quiz = pipeline.run(make_doc(), "Onboarding")

    assert quiz.items == []
    assert len(quiz.dropped) == 1
    assert "verification failed" in quiz.dropped[0].reason.lower()
