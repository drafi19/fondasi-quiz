"""Export a quiz to JSON, Markdown, or CSV."""

from __future__ import annotations

import csv
import io

from fondasi.schema import QuestionType, Quiz, QuizItem

CSV_HEADER = [
    "question",
    "type",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "correct",
    "explanation",
    "evidence_quote",
]

LETTERS = ["A", "B", "C", "D"]


def _answer_text(item: QuizItem) -> str:
    if item.type is QuestionType.short_answer:
        if item.accepted_answers:
            return item.accepted_answers[0]
        return ""
    if item.correct_index is None:
        return ""
    if 0 <= item.correct_index < len(item.options):
        return item.options[item.correct_index]
    return ""


def _answer_with_letter(item: QuizItem) -> str:
    if item.type is QuestionType.short_answer:
        return ", ".join(item.accepted_answers)
    if item.correct_index is None or not (0 <= item.correct_index < len(item.options)):
        return ""
    letter = LETTERS[item.correct_index] if item.correct_index < len(LETTERS) else ""
    return f"{letter}. {item.options[item.correct_index]}"


def to_json(quiz: Quiz) -> str:
    return quiz.model_dump_json(indent=2)


def to_markdown(quiz: Quiz) -> str:
    lines: list[str] = []
    lines.append(f"# {quiz.topic}")
    lines.append("")
    lines.append(f"Source: {quiz.source_title}")
    if quiz.source_url:
        lines.append(f"URL: {quiz.source_url}")
    lines.append("")
    lines.append("## Questions")
    lines.append("")

    for number, item in enumerate(quiz.items, start=1):
        lines.append(f"{number}. {item.prompt}")
        if item.options:
            for index, option in enumerate(item.options):
                letter = LETTERS[index] if index < len(LETTERS) else str(index + 1)
                lines.append(f"   - {letter}. {option}")
        lines.append("")

    lines.append("## Answer key")
    lines.append("")
    for number, item in enumerate(quiz.items, start=1):
        lines.append(f"{number}. **{item.type.value}**: {_answer_with_letter(item)}")
        lines.append(f"   - Explanation: {item.explanation}")
        lines.append(f"   - Evidence: \"{item.evidence_quote}\"")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def to_csv(quiz: Quiz) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    for item in quiz.items:
        options = list(item.options) + [""] * (4 - len(item.options))
        writer.writerow(
            [
                item.prompt,
                item.type.value,
                options[0],
                options[1],
                options[2],
                options[3],
                _answer_text(item),
                item.explanation,
                item.evidence_quote,
            ]
        )
    return buffer.getvalue()
