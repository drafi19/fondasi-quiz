"""The Streamlit app must generate a quiz in demo mode without network access."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from fondasi.export import to_markdown

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def _run_and_generate() -> AppTest:
    app = AppTest.from_file(str(APP), default_timeout=120).run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    return app


def test_demo_mode_generates_verified_items() -> None:
    app = _run_and_generate()
    quiz = app.session_state["fondasi_quiz"]
    assert quiz.items, "demo mode produced no items"
    assert all(item.evidence_quote for item in quiz.items)


def test_generated_quiz_exports_to_markdown() -> None:
    app = _run_and_generate()
    markdown = to_markdown(app.session_state["fondasi_quiz"])
    assert "Answer key" in markdown
