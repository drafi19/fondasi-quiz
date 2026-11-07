"""Build, Review, and Take tabs."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from fondasi.export import to_csv, to_json, to_markdown
from fondasi.extract import ExtractError, extract_from_text, extract_from_url
from fondasi.normalize import normalize_for_match
from fondasi.pipeline import BlueprintFact, QuizPipeline
from fondasi.providers import FakeProvider, ProviderError, get_provider, provider_model
from fondasi.schema import QuestionType, Quiz, QuizItem, SourceDoc
from fondasi.ui.provider_prompt import provider_dialog

DEMO_TEXT = """Fondasi is a small team that builds training material for new property agents. The onboarding program lasts three weeks and begins every Monday. Each new agent is paired with a senior mentor. Mentors meet their agents twice every week. All training notes are stored in the shared workspace. New agents may shadow a mentor on live viewings after the second week. The program ends with a short written assessment."""

DEMO_FACTS = [
    {
        "statement": "The onboarding program lasts three weeks and begins every Monday.",
        "quote": "The onboarding program lasts three weeks and begins every Monday.",
        "section": "Onboarding",
        "mcq": {
            "prompt": "How long does the onboarding program last?",
            "options": ["One week", "Two weeks", "Three weeks", "Six weeks"],
            "correct": 2,
            "explanation": "The source says the program lasts three weeks.",
        },
        "tf": {
            "prompt": "The onboarding program lasts three weeks.",
            "correct": 0,
            "explanation": "The quote states the program lasts three weeks.",
        },
        "sa": {
            "prompt": "How many weeks does the onboarding program last?",
            "accepted": ["three weeks", "3 weeks", "three"],
            "explanation": "The source gives three weeks as the duration.",
        },
    },
    {
        "statement": "Each new agent is paired with a senior mentor.",
        "quote": "Each new agent is paired with a senior mentor.",
        "section": "Mentoring",
        "mcq": {
            "prompt": "Who is each new agent paired with?",
            "options": [
                "A senior mentor",
                "A property client",
                "A marketing vendor",
                "A finance auditor",
            ],
            "correct": 0,
            "explanation": "The source pairs each new agent with a senior mentor.",
        },
        "tf": {
            "prompt": "New agents are paired with a senior mentor.",
            "correct": 0,
            "explanation": "The quote directly supports this pairing.",
        },
        "sa": {
            "prompt": "Who is each new agent paired with?",
            "accepted": ["a senior mentor", "senior mentor", "mentor"],
            "explanation": "The source names a senior mentor.",
        },
    },
    {
        "statement": "Mentors meet their agents twice every week.",
        "quote": "Mentors meet their agents twice every week.",
        "section": "Mentoring",
        "mcq": {
            "prompt": "How often do mentors meet their agents?",
            "options": ["Once a week", "Twice every week", "Once a month", "Every day"],
            "correct": 1,
            "explanation": "The source says mentors meet their agents twice every week.",
        },
        "tf": {
            "prompt": "Mentors meet their agents twice every week.",
            "correct": 0,
            "explanation": "The quote states this meeting frequency directly.",
        },
        "sa": {
            "prompt": "How often do mentors meet their agents?",
            "accepted": ["twice every week", "twice a week", "two times a week"],
            "explanation": "The source gives twice every week.",
        },
    },
    {
        "statement": "All training notes are stored in the shared workspace.",
        "quote": "All training notes are stored in the shared workspace.",
        "section": "Workspace",
        "mcq": {
            "prompt": "Where are all training notes stored?",
            "options": [
                "In the shared workspace",
                "In private email",
                "On a personal drive",
                "In a printed binder",
            ],
            "correct": 0,
            "explanation": "The quote places all training notes in the shared workspace.",
        },
        "tf": {
            "prompt": "Training notes are kept outside the shared workspace.",
            "correct": 1,
            "explanation": "The quote contradicts that claim.",
        },
        "sa": {
            "prompt": "Where are all training notes stored?",
            "accepted": ["the shared workspace", "shared workspace"],
            "explanation": "The source names the shared workspace.",
        },
    },
    {
        "statement": "The program ends with a short written assessment.",
        "quote": "The program ends with a short written assessment.",
        "section": "Assessment",
        "mcq": {
            "prompt": "How does the program end?",
            "options": [
                "With a group interview",
                "With a live viewing",
                "With a short written assessment",
                "With a vendor presentation",
            ],
            "correct": 2,
            "explanation": "The source says the program ends with a short written assessment.",
        },
        "tf": {
            "prompt": "The program ends with a short written assessment.",
            "correct": 0,
            "explanation": "The quote states the ending activity directly.",
        },
        "sa": {
            "prompt": "What does the program end with?",
            "accepted": ["a short written assessment", "written assessment", "assessment"],
            "explanation": "The source names a short written assessment.",
        },
    },
]

PROVIDER_LABELS = {
    "demo": "Demo (offline, canned)",
    "gemini": "Google Gemini",
    "openrouter": "OpenRouter",
    "commandcode": "CommandCode",
}


def _available_providers() -> list[str]:
    names = ["demo"]
    if os.getenv("GEMINI_API_KEY"):
        names.append("gemini")
    if os.getenv("OPENROUTER_API_KEY"):
        names.append("openrouter")
    if os.getenv("COMMANDCODE_API_KEY"):
        names.append("commandcode")
    return names


def _plan_types(count: int, mix: dict[QuestionType, int]) -> list[QuestionType]:
    plan: list[QuestionType] = []
    for qtype in (QuestionType.mcq, QuestionType.true_false, QuestionType.short_answer):
        plan.extend([qtype] * int(mix.get(qtype, 0)))
    if not plan:
        plan = [QuestionType.mcq]
    while len(plan) < count:
        plan.append(QuestionType.mcq)
    return plan[:count]


def _demo_item(fact: dict, qtype: QuestionType) -> dict:
    if qtype is QuestionType.mcq:
        data = fact["mcq"]
        return {
            "type": "mcq",
            "prompt": data["prompt"],
            "options": data["options"],
            "correct_index": data["correct"],
            "accepted_answers": [],
            "explanation": data["explanation"],
            "evidence_quote": fact["quote"],
        }
    if qtype is QuestionType.true_false:
        data = fact["tf"]
        return {
            "type": "true_false",
            "prompt": data["prompt"],
            "options": ["True", "False"],
            "correct_index": data["correct"],
            "accepted_answers": [],
            "explanation": data["explanation"],
            "evidence_quote": fact["quote"],
        }
    data = fact["sa"]
    return {
        "type": "short_answer",
        "prompt": data["prompt"],
        "options": [],
        "correct_index": None,
        "accepted_answers": data["accepted"],
        "explanation": data["explanation"],
        "evidence_quote": fact["quote"],
    }


def _verify_ok() -> dict:
    return {
        "supported": True,
        "answer_correct": True,
        "distractors_ok": True,
        "unique_answer": True,
        "note": "The evidence quote supports the item.",
    }


def _demo_provider(n_items: int, mix: dict[QuestionType, int]) -> FakeProvider:
    count = min(n_items, len(DEMO_FACTS))
    facts = DEMO_FACTS[:count]
    blueprint = {
        "facts": [
            {
                "statement": fact["statement"],
                "quote": fact["quote"],
                "section": fact["section"],
            }
            for fact in facts
        ],
        "note": "",
    }
    responses: list[dict] = [blueprint]
    for fact, qtype in zip(facts, _plan_types(count, mix), strict=False):
        responses.append(_demo_item(fact, qtype))
        responses.append(_verify_ok())
    return FakeProvider(responses)


def _make_pipeline(
    provider_name: str,
    n_items: int,
    mix: dict[QuestionType, int],
    on_step=None,
) -> QuizPipeline:
    if provider_name == "demo":
        provider = _demo_provider(n_items, mix)
        model = "fake"
    else:
        provider = get_provider(provider_name)
        model = getattr(provider, "model", provider_model(provider_name))
    return QuizPipeline(
        provider,
        model,
        n_items=n_items,
        mix=mix,
        on_step=on_step,
    )


def _store_quiz(quiz: Quiz, doc: SourceDoc, provider_name: str, pipeline: QuizPipeline) -> None:
    st.session_state["fondasi_quiz"] = quiz
    st.session_state["fondasi_doc"] = doc
    st.session_state["fondasi_provider"] = provider_name
    st.session_state["fondasi_pipeline"] = pipeline
    st.session_state.pop("take_result", None)


def _fact_for_item(item: QuizItem) -> BlueprintFact:
    pipeline = st.session_state.get("fondasi_pipeline")
    if pipeline is not None:
        for fact in pipeline.last_facts:
            if normalize_for_match(fact.quote) == normalize_for_match(item.evidence_quote):
                return fact
    return BlueprintFact(
        statement=item.prompt,
        quote=item.evidence_quote,
        section=item.source_section,
    )


def render_build() -> None:
    st.subheader("Build a quiz")
    st.write(
        "Paste source text or a public URL. Every generated item must point to a "
        "verbatim quote from the source."
    )

    source_text = st.text_area(
        "Source text",
        height=220,
        placeholder="Paste the article, policy, or training note here.",
    )
    url = st.text_input("Or source URL", placeholder="https://example.com/article")

    left, right = st.columns(2)
    with left:
        topic = st.text_input("Topic", placeholder="Short label for this quiz")
        n_items = st.number_input(
            "Number of items", min_value=1, max_value=8, value=5, step=1
        )
    with right:
        st.caption("Question mix")
        mcq_n = st.slider("Multiple choice", 0, 5, 3)
        tf_n = st.slider("True or false", 0, 5, 1)
        sa_n = st.slider("Short answer", 0, 5, 1)

    mix = {
        QuestionType.mcq: mcq_n,
        QuestionType.true_false: tf_n,
        QuestionType.short_answer: sa_n,
    }
    provider_options = _available_providers()
    chosen = st.session_state.get("fondasi_engine_choice")
    if chosen not in provider_options:
        provider_dialog(provider_options, PROVIDER_LABELS, "fondasi_engine_choice")
        chosen = provider_options[0]
    provider_name = st.selectbox(
        "Provider",
        provider_options,
        index=provider_options.index(chosen),
        format_func=lambda name: PROVIDER_LABELS.get(name, name),
    )
    st.session_state["fondasi_engine_choice"] = provider_name
    if provider_name == "demo":
        st.caption(
            "Demo mode ignores the pasted text and runs on a built-in sample document, "
            "with canned responses and no network calls."
        )

    progress = st.empty()
    if st.button("Generate quiz", type="primary"):
        try:
            if provider_name == "demo":
                doc = extract_from_text(DEMO_TEXT, topic or "Onboarding sample")
            elif url.strip():
                doc = extract_from_url(url.strip())
            else:
                if not source_text.strip():
                    st.error("Add source text or a URL first.")
                    st.stop()
                doc = extract_from_text(source_text, topic)
        except ExtractError as exc:
            st.error(str(exc))
            return

        def on_step(label: str, current: int, total: int) -> None:
            progress.info(label)

        try:
            pipeline = _make_pipeline(provider_name, int(n_items), mix, on_step)
            with st.spinner("Generating and verifying items..."):
                quiz = pipeline.run(doc, topic)
            _store_quiz(quiz, doc, provider_name, pipeline)
            progress.empty()
            if quiz.items:
                st.success(f"Generated {len(quiz.items)} verified items.")
            else:
                st.warning("No items survived verification. Try a richer source.")
        except ProviderError as exc:
            progress.empty()
            st.error(str(exc))
        except Exception as exc:
            progress.empty()
            st.error(f"Generation failed: {exc}")

    quiz: Quiz | None = st.session_state.get("fondasi_quiz")
    if quiz is not None:
        _render_summary(quiz)


def _render_summary(quiz: Quiz) -> None:
    st.divider()
    st.subheader("Generated quiz")
    doc = st.session_state.get("fondasi_doc")
    cols = st.columns(3)
    cols[0].metric("Items", len(quiz.items))
    cols[1].metric("Dropped", len(quiz.dropped))
    cols[2].metric("Model", quiz.model)
    st.caption(f"Topic: {quiz.topic}  |  Source: {quiz.source_title}")
    if doc is not None and doc.truncated:
        st.warning(
            f"The source was truncated to {doc.char_count} original characters "
            "worth of text. Review coverage before using the quiz."
        )

    if quiz.dropped:
        with st.expander(f"Dropped items ({len(quiz.dropped)})"):
            for dropped in quiz.dropped:
                st.write(f"- {dropped.prompt}")
                st.caption(dropped.reason)

    if quiz.items:
        for number, item in enumerate(quiz.items, start=1):
            st.markdown(f"**{number}. {item.prompt}**")
            if item.options:
                for index, option in enumerate(item.options):
                    st.write(f"- {chr(65 + index)}. {option}")
            st.caption(f"{item.type.value} | {item.explanation}")

    st.divider()
    st.caption("Export")
    json_col, md_col, csv_col = st.columns(3)
    json_col.download_button(
        "JSON",
        to_json(quiz),
        file_name="fondasi_quiz.json",
        mime="application/json",
    )
    md_col.download_button(
        "Markdown",
        to_markdown(quiz),
        file_name="fondasi_quiz.md",
        mime="text/markdown",
    )
    csv_col.download_button(
        "CSV",
        to_csv(quiz),
        file_name="fondasi_quiz.csv",
        mime="text/csv",
    )


def render_review() -> None:
    st.subheader("Review")
    quiz: Quiz | None = st.session_state.get("fondasi_quiz")
    if quiz is None:
        st.info("Build a quiz first.")
        return
    if not quiz.items:
        st.info("This quiz has no surviving items to review.")
        return

    st.write("Edit the prompt or explanation, uncheck keep to remove a row, then apply.")
    rows = [
        {
            "keep": True,
            "type": item.type.value,
            "prompt": item.prompt,
            "explanation": item.explanation,
            "id": item.id,
        }
        for item in quiz.items
    ]
    edited = st.data_editor(
        pd.DataFrame(rows),
        hide_index=True,
        num_rows="fixed",
        disabled=["type", "id"],
        column_config={
            "keep": st.column_config.CheckboxColumn("Keep", default=True),
            "type": st.column_config.TextColumn("Type"),
            "prompt": st.column_config.TextColumn("Prompt", width="large"),
            "explanation": st.column_config.TextColumn("Explanation", width="large"),
            "id": None,
        },
        key="review_" + "_".join(item.id for item in quiz.items),
    )
    if st.button("Apply edits"):
        by_id = {str(row["id"]): row for _, row in edited.iterrows()}
        kept: list[QuizItem] = []
        for item in quiz.items:
            row = by_id.get(item.id)
            if row is None or not bool(row["keep"]):
                continue
            kept.append(
                item.model_copy(
                    update={
                        "prompt": str(row["prompt"]),
                        "explanation": str(row["explanation"]),
                    }
                )
            )
        updated = quiz.model_copy(update={"items": kept})
        st.session_state["fondasi_quiz"] = updated
        st.session_state.pop("take_result", None)
        st.success("Review changes applied.")
        st.rerun()

    st.divider()
    for number, item in enumerate(quiz.items, start=1):
        with st.expander(f"{number}. {item.type.value}: {item.prompt}"):
            st.markdown("Evidence quote")
            st.markdown(f'<div class="fondasi-quote">{item.evidence_quote}</div>', unsafe_allow_html=True)
            if item.verify_note:
                st.caption(f"Verifier note: {item.verify_note}")
            if st.button("Regenerate this item", key=f"regen_{item.id}"):
                _regenerate(item)


def _regenerate(item: QuizItem) -> None:
    doc: SourceDoc = st.session_state["fondasi_doc"]
    provider_name: str = st.session_state.get("fondasi_provider", "demo")
    fact = _fact_for_item(item)
    try:
        if provider_name == "demo":
            provider = FakeProvider([item.model_dump(mode="json"), _verify_ok()])
            model = "fake"
        else:
            provider = get_provider(provider_name)
            model = provider_model(provider_name)
        pipeline = QuizPipeline(provider, model, n_items=1, mix={item.type: 1})
        regenerated = pipeline.generate_item(fact, item.type)
        verdict = pipeline.verify_item(regenerated, doc)
        if not verdict.passes:
            regenerated = pipeline.repair_item(regenerated, verdict, fact)
            verdict = pipeline.verify_item(regenerated, doc)
        if not verdict.passes:
            st.error(f"Regenerated item failed verification: {verdict.note}")
            return
        regenerated = regenerated.model_copy(
            update={"id": item.id, "verify_note": verdict.note}
        )
        quiz: Quiz = st.session_state["fondasi_quiz"]
        updated_items = [
            regenerated if existing.id == item.id else existing
            for existing in quiz.items
        ]
        st.session_state["fondasi_quiz"] = quiz.model_copy(
            update={"items": updated_items}
        )
        st.session_state.pop("take_result", None)
        st.success("Item regenerated.")
        st.rerun()
    except ProviderError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Regeneration failed: {exc}")


def _is_correct(item: QuizItem, answer: object) -> bool:
    if item.type is QuestionType.short_answer:
        text = normalize_for_match(str(answer or ""))
        return bool(text) and any(
            text == normalize_for_match(accepted) for accepted in item.accepted_answers
        )
    if answer is None or item.correct_index is None:
        return False
    try:
        chosen = item.options.index(str(answer))
    except ValueError:
        return False
    return chosen == item.correct_index


def _correct_answer(item: QuizItem) -> str:
    if item.type is QuestionType.short_answer:
        return item.accepted_answers[0] if item.accepted_answers else ""
    if item.correct_index is not None and 0 <= item.correct_index < len(item.options):
        return item.options[item.correct_index]
    return ""


def render_take() -> None:
    st.subheader("Take")
    quiz: Quiz | None = st.session_state.get("fondasi_quiz")
    if quiz is None or not quiz.items:
        st.info("Build a quiz first.")
        return

    answers: dict[str, object] = {}
    with st.form("take_quiz"):
        for number, item in enumerate(quiz.items, start=1):
            st.markdown(f"**{number}. {item.prompt}**")
            if item.type in (QuestionType.mcq, QuestionType.true_false):
                answers[item.id] = st.radio(
                    "Choose one",
                    item.options,
                    index=None,
                    key=f"take_{item.id}",
                    label_visibility="collapsed",
                )
            else:
                answers[item.id] = st.text_input(
                    "Your answer",
                    key=f"take_{item.id}",
                    label_visibility="collapsed",
                )
            st.write("")
        submitted = st.form_submit_button("Submit answers", type="primary")

    if submitted:
        results = []
        score = 0
        for item in quiz.items:
            answer = answers.get(item.id)
            correct = _is_correct(item, answer)
            score += int(correct)
            results.append(
                {
                    "prompt": item.prompt,
                    "answer": "" if answer is None else str(answer),
                    "correct": correct,
                    "correct_answer": _correct_answer(item),
                    "explanation": item.explanation,
                    "evidence_quote": item.evidence_quote,
                }
            )
        st.session_state["take_result"] = {"score": score, "results": results}

    result = st.session_state.get("take_result")
    if result:
        st.divider()
        st.metric("Score", f"{result['score']} / {len(quiz.items)}")
        for number, row in enumerate(result["results"], start=1):
            label = "Correct" if row["correct"] else "Incorrect"
            st.markdown(f"**{number}. {row['prompt']}**")
            st.write(f"{label}. Your answer: {row['answer'] or '(blank)'}")
            st.write(f"Correct answer: {row['correct_answer']}")
            st.caption(row["explanation"])
            st.markdown(f'<div class="fondasi-quote">{row["evidence_quote"]}</div>', unsafe_allow_html=True)
