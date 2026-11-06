"""Pydantic models for sources, quiz items, and complete quizzes."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class SourceDoc(BaseModel):
    """A cleaned source document used as the ground truth for a quiz."""

    title: str
    text: str
    url: str | None = None
    char_count: int
    truncated: bool = False


class QuestionType(StrEnum):
    mcq = "mcq"
    true_false = "true_false"
    short_answer = "short_answer"


class QuizItem(BaseModel):
    """One generated question. The evidence quote anchors it to the source."""

    id: str
    type: QuestionType
    prompt: str
    options: list[str] = Field(default_factory=list)
    correct_index: int | None = None
    accepted_answers: list[str] = Field(default_factory=list)
    explanation: str
    evidence_quote: str
    source_section: str | None = None
    verify_note: str | None = None

    @model_validator(mode="after")
    def _validate_by_type(self) -> QuizItem:
        if self.type is QuestionType.mcq:
            if len(self.options) != 4:
                raise ValueError("mcq items must have exactly 4 options")
            if len(set(self.options)) != 4:
                raise ValueError("mcq options must be unique")
            if self.correct_index is None or not 0 <= self.correct_index <= 3:
                raise ValueError("mcq correct_index must be between 0 and 3")
        elif self.type is QuestionType.true_false:
            pair = [option.strip().lower() for option in self.options]
            if pair not in (["true", "false"], ["benar", "salah"]):
                raise ValueError(
                    'true_false options must be ["True", "False"] or ["Benar", "Salah"]'
                )
            if self.correct_index not in (0, 1):
                raise ValueError("true_false correct_index must be 0 or 1")
        elif self.type is QuestionType.short_answer:
            non_empty = [a for a in self.accepted_answers if a.strip()]
            if not non_empty:
                raise ValueError("short_answer items need at least one accepted answer")
            if self.options:
                raise ValueError("short_answer items must not have options")
        return self


class DroppedItem(BaseModel):
    prompt: str
    reason: str


class Quiz(BaseModel):
    topic: str
    source_title: str
    source_url: str | None = None
    language: str
    items: list[QuizItem] = Field(default_factory=list)
    dropped: list[DroppedItem] = Field(default_factory=list)
    model: str
    schema_version: str = "1.0"
