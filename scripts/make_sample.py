"""Generate one sample quiz from a local source file and save it as JSON.

Usage:
    python scripts/make_sample.py --source samples/sumber/bi-shpr-2026-q3.txt \\
        --topic "Property market update, Jakarta, Q3 2026" \\
        --provider commandcode --model deepseek/deepseek-v4.1-flash-fast \\
        --out samples/jakarta-harga-properti.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fondasi.extract import extract_from_text  # noqa: E402
from fondasi.pipeline import QuizPipeline  # noqa: E402
from fondasi.providers import get_provider  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--provider", default="gemini")
    parser.add_argument("--model", default=None)
    parser.add_argument("--out", required=True)
    parser.add_argument("--n", type=int, default=5)
    args = parser.parse_args()

    text = Path(args.source).read_text(encoding="utf-8")
    doc = extract_from_text(text, args.topic)
    provider = get_provider(args.provider, model=args.model)
    model = args.model or getattr(provider, "model", args.provider)
    pipeline = QuizPipeline(
        provider,
        model,
        n_items=args.n,
        on_step=lambda label, current, total: print(f"  [{current}/{total}] {label}"),
    )
    quiz = pipeline.run(doc, args.topic)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(quiz.model_dump_json(indent=2), encoding="utf-8")

    print(f"items: {len(quiz.items)} | dropped: {len(quiz.dropped)} | model: {model}")
    for item in quiz.items:
        print(f"- [{item.type.value}] {item.prompt[:100]}")
        print(f"  quote: {item.evidence_quote[:90]}")
    for dropped in quiz.dropped:
        print(f"  DROPPED: {dropped.prompt[:70]} | {dropped.reason[:110]}")
    return 0 if quiz.items else 1


if __name__ == "__main__":
    raise SystemExit(main())
