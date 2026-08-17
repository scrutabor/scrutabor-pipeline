"""How ambiguous the corpus's forms are, measured rather than remembered.

The reader-facing /editio page tells a reader what analyzer agreement proves
and what it does not, and the load-bearing sentence is a statistic: "over
three fifths of the words in this edition have an ambiguous form — María
admits twelve readings". That number was first taken in August 2026 over NINE
texts. The corpus is now 81, and a statistic nobody can retake is a statistic
nobody can trust.

The measure is deliberately the one a reader means. A form is ambiguous when
the analyzer admits more than one PARSE for it — a part of speech plus the
features stated — regardless of which dictionary entry each parse came from.
Counting entries instead would call *Deo* ambiguous for being dative and
ablative of one noun, which is the same answer twice to a reader, and would
inflate the figure past the point of meaning anything.

Whitaker's alone answers the question. Adding Collatinus's readings to the
same pool double-counts every parse the two agree on, and the union of two
differently-shaped feature vocabularies is not a count of readings — it is a
count of ways of saying them. The agreement machinery in `agree.py` exists
precisely to reconcile the two vocabularies token by token, and it is the
right tool for a verdict on ONE word, not for a population statistic.

Run it:  python -m scrutabor_pipeline.ambiguity ../scrutabor-corpus
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys

from scrutabor_pipeline import (
    compat,  # noqa: F401  (pycollatinus shim)
    whitakers,
)


def corpus_forms(corpus: pathlib.Path) -> list[str]:
    """Every word token of every text, in order, as the corpus prints it."""
    forms: list[str] = []
    for path in sorted((corpus / "texts").rglob("*.json")):
        doc = json.loads(path.read_text())
        for segment in doc["segments"]:
            for word in segment.get("words") or []:
                forms.append(word["form"])
    return forms


def parses(form: str) -> set[tuple]:
    """The distinct parses this form admits: (pos, features), deduplicated."""
    return {(c.pos, tuple(sorted(c.feature_dict().items()))) for c in whitakers.candidates(form)}


def measure(corpus: pathlib.Path) -> dict:
    forms = corpus_forms(corpus)
    distinct = sorted(set(forms))
    counts = {f: len(parses(f)) for f in distinct}
    ambiguous = sum(1 for f in forms if counts[f] > 1)
    unknown = sum(1 for f in forms if counts[f] == 0)
    return {
        "tokens": len(forms),
        "distinct_forms": len(distinct),
        "ambiguous_tokens": ambiguous,
        "ambiguous_share": ambiguous / len(forms),
        "unknown_tokens": unknown,
        "histogram": dict(sorted(collections.Counter(min(counts[f], 6) for f in forms).items())),
        "maria": counts.get("María", 0),
    }


def main(argv: list[str]) -> int:
    corpus = pathlib.Path(argv[1] if len(argv) > 1 else "../scrutabor-corpus")
    if not (corpus / "texts").is_dir():
        print(f"no corpus at {corpus}", file=sys.stderr)
        return 2
    m = measure(corpus)
    print(f"tokens                {m['tokens']}")
    print(f"distinct forms        {m['distinct_forms']}")
    print(f"ambiguous tokens      {m['ambiguous_tokens']}  ({m['ambiguous_share']:.1%})")
    print(f"unknown to Whitaker's {m['unknown_tokens']}")
    print(f"parses of María       {m['maria']}")
    print(f"tokens by parse count {m['histogram']}  (6+ collapsed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
