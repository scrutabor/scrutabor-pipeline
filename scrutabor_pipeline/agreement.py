"""Run the source-agreement report over a corpus checkout.

Usage: python -m scrutabor_pipeline.agreement <path-to-scrutabor-corpus>

The verdict names its subject: texts, tokens, and per-verdict counts; a
report that checks nothing must not pass (exit 2 on zero tokens). Exit 0
also when divergences exist — the report is a measurement, the review
queue is its output; gating happens in the corpus repo once findings are
adjudicated there.
"""

import json
import sys
from collections import Counter
from pathlib import Path

from .agree import compare


def run(corpus: Path):
    verdicts = []
    texts = 0
    for text_path in sorted(corpus.glob("texts/*/*.json")):
        doc = json.loads(text_path.read_text(encoding="utf-8"))
        texts += 1
        for segment in doc["segments"]:
            for word in segment.get("words") or []:
                verdicts.append(compare(doc["id"], word))
    return texts, verdicts


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m scrutabor_pipeline.agreement <corpus-path>")
        return 2
    corpus = Path(argv[1])
    texts, verdicts = run(corpus)
    if not verdicts:
        print("VERDICT FAIL tokens=0 — refusing to pass on zero")
        return 2

    counts = Counter(v.verdict for v in verdicts)
    by_sources = Counter(v.sources for v in verdicts if v.verdict.startswith("AGREE"))
    for v in verdicts:
        if v.verdict != "AGREE":
            print(f"{v.verdict:15} {v.token_ref:35} {v.detail}")

    queue = [
        {"token": v.token_ref, "verdict": v.verdict, "detail": v.detail}
        for v in verdicts
        if v.verdict == "DIVERGE"
    ]
    queue_path = Path("review-queue.json")
    queue_path.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    subject = " ".join(f"{k.lower()}={counts.get(k, 0)}" for k in
                       ("AGREE", "AGREE_RULED", "AGREE_FORM_ONLY", "EDITORIAL_ONLY", "DIVERGE", "FORM_ABSENT"))
    breakdown = " ".join(f"{k}={n}" for k, n in sorted(by_sources.items()))
    print(f"VERDICT OK texts={texts} tokens={len(verdicts)} {subject} [{breakdown}] queue={len(queue)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
