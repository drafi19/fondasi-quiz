"""The generation pipeline: blueprint, generate, verify, repair, clean."""

from __future__ import annotations

import json
import uuid
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from fondasi.normalize import is_quote_in_source, normalize_for_match
from fondasi.providers.base import Provider, ProviderError
from fondasi.schema import DroppedItem, QuestionType, Quiz, QuizItem, SourceDoc

PROMPT_DIR = Path(__file__).parent / "prompts"

DEFAULT_MIX: dict[QuestionType, int] = {
    QuestionType.mcq: 3,
    QuestionType.true_false: 1,
    QuestionType.short_answer: 1,
}

BLUEPRINT_HINT = '{"facts":[{"statement":"string","quote":"string","section":"string"}],"note":"string"}'
ITEM_HINT = (
    '{"type":"mcq|true_false|short_answer","prompt":"string","options":["string"],'
    '"correct_index":0,"accepted_answers":["string"],"explanation":"string",'
    '"evidence_quote":"string"}'
)
VERIFY_HINT = (
    '{"supported":true,"answer_correct":true,"distractors_ok":true,'
    '"unique_answer":true,"note":"one sentence"}'
)


class BlueprintFact(BaseModel):
    statement: str
    quote: str
    section: str | None = None


class BlueprintResponse(BaseModel):
    facts: list[BlueprintFact] = Field(default_factory=list)
    note: str | None = None


class GeneratePayload(BaseModel):
    type: QuestionType
    prompt: str
    options: list[str] = Field(default_factory=list)
    correct_index: int | None = None
    accepted_answers: list[str] = Field(default_factory=list)
    explanation: str
    evidence_quote: str


class VerifyPayload(BaseModel):
    supported: bool
    answer_correct: bool
    distractors_ok: bool
    unique_answer: bool
    note: str


@dataclass
class Verdict:
    supported: bool
    answer_correct: bool
    distractors_ok: bool
    unique_answer: bool
    note: str

    @property
    def passes(self) -> bool:
        return (
            self.supported
            and self.answer_correct
            and self.distractors_ok
            and self.unique_answer
        )


@dataclass
class RejectedFact:
    fact: BlueprintFact
    reason: str


@cache
def load_prompt(name: str) -> str:
    return (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")


def _is_transient(exc: BaseException) -> bool:
    return isinstance(exc, ProviderError) and exc.transient


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class QuizPipeline:
    def __init__(
        self,
        provider: Provider,
        model: str,
        *,
        n_items: int = 5,
        mix: dict[QuestionType, int] | None = None,
        max_source_words: int = 6000,
        on_step: Callable[[str, int, int], None] | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.n_items = max(1, n_items)
        self.mix = dict(mix or DEFAULT_MIX)
        self.max_source_words = max_source_words
        self.on_step = on_step
        self.last_facts: list[BlueprintFact] = []

    @retry(
        retry=retry_if_exception(_is_transient),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    def _provider_call(self, system: str, user: str, schema_hint: str) -> dict:
        return self.provider.generate_json(system, user, schema_hint)

    def _report(self, label: str, current: int, total: int) -> None:
        if self.on_step is not None:
            self.on_step(label, current, total)

    def build_blueprint(
        self, doc: SourceDoc, n: int
    ) -> tuple[list[BlueprintFact], list[RejectedFact]]:
        system = load_prompt("blueprint")
        user = (
            f"N: {n}\n"
            f"Source title: {doc.title}\n"
            f"Source language: use the language of the text below.\n\n"
            f"SOURCE TEXT:\n{doc.text}"
        )
        raw = self._provider_call(system, user, BLUEPRINT_HINT)
        try:
            payload = BlueprintResponse.model_validate(raw)
        except ValidationError as exc:
            raise ProviderError(f"Blueprint JSON did not match the schema: {exc}") from exc

        surviving: list[BlueprintFact] = []
        rejected: list[RejectedFact] = []
        for fact in payload.facts:
            if not fact.statement.strip():
                rejected.append(RejectedFact(fact, "Fact statement is empty."))
                continue
            if not is_quote_in_source(fact.quote, doc.text):
                rejected.append(
                    RejectedFact(fact, "Quote is not a verbatim substring of the source.")
                )
                continue
            surviving.append(fact)
        return surviving, rejected

    def generate_item(self, fact: BlueprintFact, qtype: QuestionType) -> QuizItem:
        system = load_prompt("generate")
        user = (
            f"Requested question type: {qtype.value}\n"
            f"Fact: {fact.statement}\n"
            f"Verified quote: {fact.quote}\n"
            f"Section: {fact.section or ''}\n"
        )
        raw = self._provider_call(system, user, ITEM_HINT)
        payload = self._parse_payload(raw, "generate")
        if payload.type is not qtype:
            raise ProviderError(
                f"Generator returned type {payload.type.value} but {qtype.value} was requested."
            )
        return self._payload_to_item(payload, qtype, fact.section)

    def verify_item(self, item: QuizItem, doc: SourceDoc) -> Verdict:
        system = load_prompt("verify")
        user = (
            f"SOURCE TEXT:\n{doc.text}\n\n"
            f"EVIDENCE QUOTE:\n{item.evidence_quote}\n\n"
            f"ITEM:\n{json.dumps(item.model_dump(mode='json'), ensure_ascii=False)}"
        )
        raw = self._provider_call(system, user, VERIFY_HINT)
        try:
            payload = VerifyPayload.model_validate(raw)
        except ValidationError as exc:
            raise ProviderError(f"Verify JSON did not match the schema: {exc}") from exc
        return Verdict(
            supported=payload.supported,
            answer_correct=payload.answer_correct,
            distractors_ok=payload.distractors_ok,
            unique_answer=payload.unique_answer,
            note=payload.note,
        )

    def repair_item(
        self, item: QuizItem, verdict: Verdict, fact: BlueprintFact
    ) -> QuizItem:
        system = load_prompt("repair")
        user = (
            f"ORIGINAL ITEM:\n{json.dumps(item.model_dump(mode='json'), ensure_ascii=False)}\n\n"
            f"FAILURE NOTE:\n{verdict.note}\n\n"
            f"FACT:\n{fact.statement}\n\n"
            f"VERBATIM QUOTE:\n{fact.quote}\n"
        )
        raw = self._provider_call(system, user, ITEM_HINT)
        payload = self._parse_payload(raw, "repair")
        if payload.type is not item.type:
            raise ProviderError(
                f"Repair returned type {payload.type.value} but {item.type.value} was expected."
            )
        return self._payload_to_item(payload, item.type, item.source_section, item.id)

    def run(self, doc: SourceDoc, topic: str) -> Quiz:
        facts, _rejected = self.build_blueprint(doc, self.n_items)
        self.last_facts = facts
        types = self._question_type_plan(len(facts))
        items: list[QuizItem] = []
        dropped: list[DroppedItem] = []

        total = len(facts)
        for index, fact in enumerate(facts, start=1):
            qtype = types[index - 1] if index - 1 < len(types) else QuestionType.mcq
            self._report(f"Generating item {index} of {total}", index, total)
            try:
                item = self.generate_item(fact, qtype)
            except ProviderError as exc:
                dropped.append(DroppedItem(prompt=fact.statement, reason=str(exc)))
                continue

            verdict = self.verify_item(item, doc)
            if not verdict.passes:
                try:
                    item = self.repair_item(item, verdict, fact)
                    verdict = self.verify_item(item, doc)
                except ProviderError as exc:
                    dropped.append(
                        DroppedItem(
                            prompt=item.prompt,
                            reason=f"Repair failed: {exc}",
                        )
                    )
                    continue

            if verdict.passes:
                item = item.model_copy(update={"verify_note": verdict.note})
                items.append(item)
            else:
                dropped.append(
                    DroppedItem(
                        prompt=item.prompt,
                        reason=f"Verification failed after one repair: {verdict.note}",
                    )
                )

        quiz = Quiz(
            topic=topic.strip() or doc.title,
            source_title=doc.title,
            source_url=doc.url,
            language="source",
            items=items,
            dropped=dropped,
            model=self.model,
        )
        return self.mechanical_checks(quiz, doc)

    def mechanical_checks(self, quiz: Quiz, doc: SourceDoc) -> Quiz:
        kept: list[QuizItem] = []
        dropped = list(quiz.dropped)
        seen_prompts: set[str] = set()

        for item in quiz.items:
            if not is_quote_in_source(item.evidence_quote, doc.text):
                dropped.append(
                    DroppedItem(
                        prompt=item.prompt,
                        reason="Evidence quote is not a verbatim substring of the source.",
                    )
                )
                continue

            prompt_key = normalize_for_match(item.prompt)
            if prompt_key in seen_prompts:
                dropped.append(
                    DroppedItem(prompt=item.prompt, reason="Duplicate prompt.")
                )
                continue
            seen_prompts.add(prompt_key)
            kept.append(item)

        total = len(kept)
        cap = int(total * 0.6)
        if total >= 2 and cap >= 1:
            section_counts = Counter(
                item.source_section for item in kept if item.source_section
            )
            crowded = {section for section, count in section_counts.items() if count > cap}
            if crowded:
                final: list[QuizItem] = []
                used: Counter[str] = Counter()
                for item in kept:
                    section = item.source_section
                    if section in crowded:
                        if used[section] >= cap:
                            dropped.append(
                                DroppedItem(
                                    prompt=item.prompt,
                                    reason=(
                                        "Too many items came from section "
                                        f"'{section}'; the surplus was dropped."
                                    ),
                                )
                            )
                            continue
                        used[section] += 1
                    final.append(item)
                kept = final

        return quiz.model_copy(update={"items": kept, "dropped": dropped})

    def _question_type_plan(self, count: int) -> list[QuestionType]:
        order = [
            QuestionType.mcq,
            QuestionType.true_false,
            QuestionType.short_answer,
        ]
        weights = {qtype: max(0, int(self.mix.get(qtype, 0))) for qtype in order}
        if not any(weights.values()):
            weights[QuestionType.mcq] = 1
        positive = [qtype for qtype in order if weights[qtype] > 0]
        total_weight = sum(weights.values())

        exact = {qtype: count * weights[qtype] / total_weight for qtype in order}
        plan_counts = {qtype: int(exact[qtype]) for qtype in order}

        # With a small item count the floor leaves some types at zero. Give every
        # requested type one slot when there is room, then rebalance the surplus.
        if count >= len(positive):
            for qtype in positive:
                plan_counts[qtype] = max(plan_counts[qtype], 1)
        while sum(plan_counts.values()) > count:
            floors = {qtype: 1 if qtype in positive and count >= len(positive) else 0 for qtype in order}
            donors = [qtype for qtype in order if plan_counts[qtype] > floors[qtype]]
            if not donors:
                break
            plan_counts[max(donors, key=lambda qtype: plan_counts[qtype])] -= 1

        missing = count - sum(plan_counts.values())
        ranked = sorted(
            order,
            key=lambda qtype: (-(exact[qtype] - int(exact[qtype])), order.index(qtype)),
        )
        for qtype in ranked:
            if missing <= 0:
                break
            if weights[qtype] > 0:
                plan_counts[qtype] += 1
                missing -= 1

        plan: list[QuestionType] = []
        for qtype in order:
            plan.extend([qtype] * plan_counts[qtype])
        return plan[:count]

    def _parse_payload(self, raw: dict, stage: str) -> GeneratePayload:
        try:
            return GeneratePayload.model_validate(raw)
        except ValidationError as exc:
            raise ProviderError(f"{stage} JSON did not match the schema: {exc}") from exc

    def _payload_to_item(
        self,
        payload: GeneratePayload,
        qtype: QuestionType,
        section: str | None,
        item_id: str | None = None,
    ) -> QuizItem:
        try:
            return QuizItem(
                id=item_id or _new_id(),
                type=qtype,
                prompt=payload.prompt,
                options=payload.options,
                correct_index=payload.correct_index,
                accepted_answers=payload.accepted_answers,
                explanation=payload.explanation,
                evidence_quote=payload.evidence_quote,
                source_section=section or None,
            )
        except ValidationError as exc:
            raise ProviderError(f"Generated item failed schema validation: {exc}") from exc
