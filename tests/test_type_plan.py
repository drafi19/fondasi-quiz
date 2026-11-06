"""The type plan must survive small item counts."""

from __future__ import annotations

from collections import Counter

from fondasi.pipeline import QuizPipeline
from fondasi.providers.fake import FakeProvider
from fondasi.schema import QuestionType


def _plan(count: int) -> Counter[str]:
    pipeline = QuizPipeline(FakeProvider([]), "demo", n_items=count)
    return Counter(qtype.value for qtype in pipeline._question_type_plan(count))


def test_plan_keeps_every_type_when_count_matches_the_mix() -> None:
    plan = _plan(5)
    assert plan == Counter({"mcq": 3, "true_false": 1, "short_answer": 1})


def test_plan_keeps_variety_at_three_items() -> None:
    plan = _plan(3)
    assert sum(plan.values()) == 3
    assert set(plan) == {"mcq", "true_false", "short_answer"}


def test_plan_falls_back_to_mcq_for_one_item() -> None:
    plan = _plan(1)
    assert plan == Counter({"mcq": 1})


def test_plan_scales_up_with_the_same_ratio() -> None:
    plan = _plan(10)
    assert plan == Counter({"mcq": 6, "true_false": 2, "short_answer": 2})


def test_plan_respects_a_custom_mix() -> None:
    pipeline = QuizPipeline(
        FakeProvider([]),
        "demo",
        mix={QuestionType.mcq: 1, QuestionType.true_false: 1, QuestionType.short_answer: 0},
    )
    plan = Counter(qtype.value for qtype in pipeline._question_type_plan(4))
    assert plan == Counter({"mcq": 2, "true_false": 2})
