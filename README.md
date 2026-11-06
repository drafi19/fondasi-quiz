# Fondasi

Fondasi is a source-grounded quiz generator for internal training material. You paste a source text or a public URL, and it produces multiple choice, true or false, and short answer items that each cite a verbatim quote from the source. Items that cannot be traced back to the source are dropped instead of silently repaired.

## What problem it solves, and who it is for

Training teams often need a quick quiz from a policy page, a handbook section, or an internal briefing. Writing those questions by hand is slow, and asking a general model to write them from memory produces plausible questions that are not actually in the source. Fondasi is for instructional designers, operations leads, and subject matter experts who need a first draft they can review, edit, and export without losing the link to the original text.

## How it works

```text
source text or URL
        |
        v
  extract.py  ->  SourceDoc
        |
        v
  blueprint.md  ->  candidate facts + verbatim quotes
        |
        v
  generate.md  ->  one quiz item per fact
        |
        v
  verify.md  ->  strict verdict
        |
        +---- fail ---->  repair.md once  ->  verify again
        |
        v
  mechanical_checks  ->  evidence, duplicates, section balance
        |
        v
  Review tab  ->  edit, delete, regenerate
        |
        v
  export: JSON, Markdown, CSV
```

**Extraction.** `extract_from_text` strips and truncates pasted text to the configured word cap. `extract_from_url` fetches a page with a normal user agent, then uses `trafilatura` to pull readable article text and title. There is no JavaScript rendering, so pages that need a browser may fail with a readable error.

**Blueprint.** The model reads the source and proposes candidate facts. Each candidate carries a single quote that must be at least six words long. The pipeline validates the JSON with Pydantic, then drops any fact whose quote is not a verbatim substring of the source after normalization.

**Generation.** For each surviving fact, the pipeline asks for one item of the planned type. The generation prompt has different rules for multiple choice, true or false, and short answer, and it must return the same JSON shape every time.

**Verification.** A separate reviewer prompt checks four things: whether the answer is supported by the quote alone, whether the marked answer is correct, whether every distractor is definitely wrong, and whether the answer is unique. All four must be true for the item to pass.

**Repair.** A failed item gets exactly one rewrite attempt. The repair prompt receives the original item, the failure note, the fact, and the quote. The rewritten item is verified once more. A second failure drops the item and records the reason.

**Mechanical checks.** The pipeline independently checks the evidence quote again, removes duplicate prompts after normalization, and enforces a source-section balance rule. These checks do not ask a model for an opinion.

**Review and export.** The Review tab lets a human edit prompts and explanations, remove rows, or regenerate a single item. The export layer writes JSON, Markdown with a separate answer key, and CSV with a fixed column order.

## Why the evidence quote rule exists

The rule exists because a generated quiz can look convincing while being disconnected from the document it claims to teach. Requiring a verbatim quote forces every item to point at a specific piece of evidence that a reviewer can check in seconds. It also makes silent hallucination visible: if the model paraphrases, invents a quote, or merges two sentences, the item fails the substring check and is dropped.

The rule does not guarantee that the item is pedagogically good, free of ambiguity, or correctly answered. A real sentence can still be quoted out of context, and a distractor can still be too close to the key. That is why the pipeline has a separate verifier, a human review screen, and a `verify_note` on each item. The quote check proves provenance, not quality.

## Prompt design

The four prompts are separate because they ask for different kinds of thinking and they fail in different ways.

- `blueprint.md` selects facts from the source. It is not allowed to write questions yet, which keeps it focused on coverage and quote fidelity.
- `generate.md` writes one item for one fact and one question type. Splitting this from the blueprint keeps the question rules short and type specific.
- `verify.md` is a strict reviewer. It sees the source, the quote, and one item, and must answer four concrete booleans. Keeping review separate from generation makes it easier to be strict without also asking the model to be creative.
- `repair.md` fixes one rejected item using the verifier's note. It is separate so the original failure stays visible and the rewrite is constrained to the same quote.

All four prompts tell the model to write question text and explanations in the source language, not in English by default.

## Model choice and provider abstraction

The app talks to providers through one small interface: `generate_json(system, user, schema_hint) -> dict`. That keeps the pipeline independent of any vendor and makes the test suite fully offline with `FakeProvider`.

The included providers are Gemini, OpenRouter, and CommandCode. Gemini uses its REST JSON mode. OpenRouter and CommandCode use OpenAI-compatible chat completions with a JSON response format. Model names come from environment variables, with sensible defaults in `fondasi/config.py`. API keys are read from the environment only. No key is written into a file, and `.env.example` contains variable names with empty values.

## Sample runs

Two runs are committed, generated with `scripts/make_sample.py` and the CommandCode provider on `deepseek/deepseek-v4.1-flash-fast`:

| File | Source | Items | Dropped |
|---|---|---|---|
| `samples/jakarta-harga-properti.json` | Bank Indonesia, residential property price survey Q3 2026, published 6 November 2026 | 4 | 0 |
| `samples/kpr-flpp.json` | Ministry of Housing and Settlement Areas (PKP), FLPP and KUR Perumahan release, 2 November 2026 | 5 | 0 |

The Bank Indonesia run asked for five items and kept four. The blueprint rule against testing the same indicator twice rejected the second growth figure for the same index, so the run produced fewer items instead of a near duplicate. That is the intended behaviour.

## What broke

These are the real failures hit while building this, including the ones that only appeared when a live model was called.

- **The model picker was a label, not a switch.** The first live run returned `400 unsupported_model` for `commandcode-default`. The pipeline received a model name for its metadata, but the provider built its own model from the environment at construction time, so the displayed model and the requested model could differ. Fixed by letting `get_provider(name, model=...)` pass an override through, and by reporting `provider.model` in the quiz instead of the config default.
- **URL extraction can return navigation instead of the article.** On a Rumah123 guide page, `trafilatura` returned 40,365 characters of menus and location links. The article body only started around line 228, and the escaped markdown in that body would have produced unusable quotes. Pasted text is therefore the primary path. URL extraction stays for article-shaped pages, and the UI shows the extracted title and length so the user can see what the model actually received.
- **The question type mix disappeared at small item counts.** With five items the plan produced three multiple choice, one true or false, and one short answer. With three items it produced three multiple choice, because the plan was built in type order and then truncated. Fixed with proportional allocation plus a minimum of one slot per requested type, covered by `tests/test_type_plan.py`.
- **Two questions ended up measuring the same indicator.** The first blueprint for the Bank Indonesia release proposed both the Q3 and the Q2 growth rate for the same index. The duplicate check only compared exact prompt text, so both survived. Fixed in the prompt with a rule that facts must be about different claims. A semantic duplicate check is still on the list.
- **Python 3.13 deprecations.** `class QuestionType(str, Enum)` and `@lru_cache(maxsize=None)` were both flagged during the build; they became `StrEnum` and `functools.cache`.
- **The schema rejected a correct Indonesian true or false item.** The validator insisted on the English pair `["True", "False"]` while the prompt asked for output in the source language, so the first Indonesian run lost an item to a validation error. Fixed by accepting either `["True", "False"]` or `["Benar", "Salah"]`.

## Next changes

- Compare items by meaning, not by exact prompt text, so near duplicates like the two IHPR questions are caught before a human has to spot them.
- Check the whole document when verifying a number, not just the quote, so a source that contradicts itself gets flagged instead of quoted selectively.
- Add a coverage view showing which parts of the source never produced a question.

## Limitations

- The verifier is still a model. It can be confidently wrong, and the four booleans are only as good as the prompt and the quote.
- The pipeline makes several calls per item. That is slow and costs more than a single prompt, which is a deliberate trade for traceability.
- URL extraction works best on article-shaped pages. JavaScript-heavy pages, paywalls, and PDFs are out of scope.
- The section balance rule is intentionally simple. It counts labels and caps crowded sections, but it does not understand topic coverage.
- The Take tab is a lightweight self-check, not a proctored assessment. It does not save attempts or support classrooms.
- The demo provider is canned. It is useful for a quick offline look, not for real content.

## Run locally

Requires Python 3.13 and `uv`.

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/Scripts/python.exe -e ".[dev]"
uv run pytest -q
uv run ruff check .
uv run streamlit run streamlit_app.py
```

The test suite uses `FakeProvider` and makes no network calls. The Streamlit app starts with the offline demo provider selected by default.

To use a real provider, copy `.env.example` to `.env`, fill in the key you need, and export the values into your shell before starting the app. The names are `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, and `COMMANDCODE_API_KEY`. Optional model overrides are `GEMINI_MODEL`, `OPENROUTER_MODEL`, and `COMMANDCODE_MODEL`.

Headless smoke check:

```bash
uv run streamlit run streamlit_app.py --server.headless true --server.port 8599
```

## Decisions I made alone

- The default mix is three multiple choice, one true or false, and one short answer, matching the requested example.
- The `language` field stores `"source"` rather than guessing a language code. Guessing from a short document would be unreliable, and the prompts already enforce source-language output.
- `char_count` records the cleaned source length before truncation, so the UI can warn when text was cut.
- The section balance rule uses `floor(0.6 * total items)` as the cap and only applies to items that have a non-empty `source_section`. Items without a section are not grouped together.
- The repair flow allows one repair attempt, then one more verification, exactly as specified. There is no silent third attempt.
- The demo source is fictional and clearly internal. It contains no claims about any real company or the property market.
- The demo provider is rebuilt on each generation so the scripted responses are not exhausted by Streamlit reruns.
- `pandas` is not listed directly in `requirements.txt` because Streamlit already depends on it and the app only uses it for `st.data_editor`.
- The Markdown export uses letter labels for options and a separate answer key with explanations and quotes.
- The app hides the Streamlit menu and footer in CSS, uses a centered 880px content column, and avoids shadows, gradients, and glow.
