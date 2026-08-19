"""Run the source-agreement report over a corpus checkout.

Usage: python -m scrutabor_pipeline.agreement <path-to-scrutabor-corpus>

The verdict names its subject: texts, tokens, and per-verdict counts; a
report that checks nothing must not pass (exit 2 on zero tokens). Exit 0
also when divergences exist — the report is a measurement, the review
queue is its output; gating happens in the corpus repo once findings are
adjudicated there.

It also checks PROVENANCE: since corpus schema 0.7.0 every word names the
analyzers that confirm it, and a name is only worth something if someone
verifies it. Twice this was done by a throwaway script, and twice it found
a real error, so it lives here now — the report already knows exactly who
confirmed each token, and comparing that against what the corpus claims
costs nothing. Reported as `provenance_mismatch=N`.
"""

import json
import sys
from collections import Counter
from pathlib import Path

from .agree import compare

# Sources that are not analyzers: our own work, and the witnesses, whose
# names this report has no opinion about.
ANALYZERS = {"whitakers", "collatinus"}


def declared_analyzers(doc: dict, word: dict) -> set[str]:
    """What the corpus claims confirms this word, per SCHEMA.md's cascade:
    a word's own analysis, else the document's word default, else the
    document default.

    BOTH SHAPES, and that is not politeness. Corpus schema 0.14.0 joined each
    text into one document and moved every editorial claim under `editorial`,
    so the pre-0.14.0 lookup found nothing and this report said every word
    claimed no analyzer -- silently, because its own test still built the old
    shape and so stayed green while describing a corpus that had stopped
    existing. The older shape is still read because the pipeline is not
    versioned with the corpus and may be pointed at an older checkout.
    """
    editorial = doc.get("editorial") or {}
    analysis = (
        (editorial.get("words") or {}).get(word.get("id"), {}).get("analysis")
        or word.get("analysis")
        or editorial.get("analysis_defaults_words")
        or editorial.get("analysis_defaults")
        or doc.get("analysis_defaults_words")
        or doc.get("analysis_defaults")
        or {}
    )
    return {s for s in analysis.get("sources", []) if s in ANALYZERS}


def run(corpus: Path):
    verdicts = []
    provenance = []
    texts = 0
    for text_path in sorted(corpus.glob("texts/*/*.json")):
        doc = json.loads(text_path.read_text(encoding="utf-8"))
        texts += 1
        for segment in doc["segments"]:
            for word in segment.get("words") or []:
                verdict = compare(doc["id"], word)
                verdicts.append(verdict)
                claimed = declared_analyzers(doc, word)
                confirming = {s for s in verdict.sources.split("+") if s in ANALYZERS}
                if claimed != confirming:
                    provenance.append(
                        f"{verdict.token_ref}: claims {sorted(claimed) or ['-']}, "
                        f"confirmed by {sorted(confirming) or ['-']}"
                    )
    return texts, verdicts, provenance


def main(argv: list[str]) -> int:
    strict = "--strict" in argv
    argv = [a for a in argv if a != "--strict"]
    if len(argv) != 2:
        print("usage: python -m scrutabor_pipeline.agreement [--strict] <corpus-path>")
        return 2
    corpus = Path(argv[1])
    texts, verdicts, provenance = run(corpus)
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

    subject = " ".join(
        f"{k.lower()}={counts.get(k, 0)}"
        for k in (
            "AGREE",
            "AGREE_RULED",
            "AGREE_FORM_ONLY",
            "EDITORIAL_ONLY",
            "DIVERGE",
            "FORM_ABSENT",
        )
    )
    breakdown = " ".join(f"{k or 'none'}={n}" for k, n in sorted(by_sources.items()))
    for line in provenance:
        print(f"PROVENANCE      {line}")
    # TWO FAILURE MODES, told apart on purpose.
    #
    # Plain: the machine must RUN. That is what CI asks, and it is the class
    # that was actually broken -- one unhandled exception on one word left the
    # whole report unproducible from 2026-08-18 and nothing said so. A crash
    # exits non-zero by itself, which is the point of running it at all.
    #
    # `--strict` additionally refuses a corpus that CLAIMS confirmations the
    # analyzers contradict. That is the corpus's defect and not the pipeline's,
    # so it is opt-in: this workflow is pointed at whatever corpus main holds,
    # and a repository should not go red for another repository's content. The
    # corpus's own release ritual is where --strict belongs.
    ok = "OK" if not (strict and provenance) else "FAIL"
    print(
        f"VERDICT {ok} texts={texts} tokens={len(verdicts)} {subject} [{breakdown}] "
        f"queue={len(queue)} provenance_mismatch={len(provenance)}"
    )
    return 1 if (strict and provenance) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
