"""Extract clean source text from pasted text or a public URL."""

from __future__ import annotations

import httpx
import trafilatura

from fondasi.config import max_source_words
from fondasi.schema import SourceDoc

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 FondasiQuiz/0.1"
)


class ExtractError(Exception):
    """Raised when a source cannot be fetched or parsed."""


def _truncate(text: str) -> tuple[str, bool]:
    limit = max_source_words()
    words = text.split()
    if len(words) <= limit:
        return text, False
    return " ".join(words[:limit]), True


def _guess_title(text: str, topic: str) -> str:
    """Use the first line when it reads like a headline, otherwise the topic."""
    first_line = text.strip().splitlines()[0].strip() if text.strip() else ""
    if first_line and len(first_line) <= 120:
        return first_line
    return topic.strip() or "Untitled source"


def extract_from_text(text: str, topic: str) -> SourceDoc:
    """Build a SourceDoc from pasted text, truncating long input."""
    cleaned = text.strip()
    if not cleaned:
        raise ExtractError("The source text is empty.")
    full_length = len(cleaned)
    truncated_text, truncated = _truncate(cleaned)
    return SourceDoc(
        title=_guess_title(cleaned, topic),
        text=truncated_text,
        url=None,
        char_count=full_length,
        truncated=truncated,
    )


def extract_from_url(url: str) -> SourceDoc:
    """Fetch a URL and extract readable text without rendering JavaScript."""
    try:
        response = httpx.get(
            url,
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ExtractError(f"Could not fetch {url}: {exc}") from exc

    html = response.text
    try:
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
        )
    except Exception as exc:
        raise ExtractError(f"Could not parse {url}: {exc}") from exc

    if not text or not text.strip():
        raise ExtractError(f"No readable article text found at {url}.")

    title = url
    try:
        metadata = trafilatura.extract_metadata(html)
        if metadata and metadata.title:
            title = metadata.title
    except Exception:
        pass

    cleaned = text.strip()
    full_length = len(cleaned)
    truncated_text, truncated = _truncate(cleaned)
    return SourceDoc(
        title=title,
        text=truncated_text,
        url=url,
        char_count=full_length,
        truncated=truncated,
    )
