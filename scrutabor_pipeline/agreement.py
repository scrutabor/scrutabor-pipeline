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

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from .agree import Verdict, compare

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
    confirmations = []
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
                confirmations.append(
                    {
                        "token": verdict.token_ref,
                        "verdict": verdict.verdict,
                        "declared": sorted(claimed),
                        "confirmed": sorted(confirming),
                    }
                )
                if claimed != confirming:
                    provenance.append(
                        f"{verdict.token_ref}: claims {sorted(claimed) or ['-']}, "
                        f"confirmed by {sorted(confirming) or ['-']}"
                    )
    return texts, verdicts, provenance, confirmations


def corpus_identity(corpus: Path) -> dict[str, str | None]:
    digest = hashlib.sha256()
    for path in sorted(corpus.glob("texts/*/*.json")):
        digest.update(str(path.relative_to(corpus)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    try:
        commit = subprocess.check_output(
            ["git", "-C", str(corpus), "rev-parse", "HEAD"], text=True
        ).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        commit = None
    return {"commit": commit, "texts_sha256": digest.hexdigest()}


def pipeline_identity() -> dict[str, str | bool | None]:
    root = Path(__file__).resolve().parent.parent
    digest = hashlib.sha256()
    for path in sorted((root / "scrutabor_pipeline").glob("*.py")):
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    try:
        commit = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()
        dirty = bool(
            subprocess.check_output(
                ["git", "-C", str(root), "status", "--porcelain"], text=True
            ).strip()
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        commit = None
        dirty = True
    return {
        "commit": commit,
        "dirty": dirty,
        "source_sha256": digest.hexdigest(),
    }


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def confirmation_attestation(
    corpus: Path,
    texts: int,
    verdicts: list[Verdict],
    provenance: list[str],
    confirmations: list[dict],
    *,
    include_confirmations: bool = False,
) -> dict:
    root = hashlib.sha256(
        json.dumps(
            confirmations,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    groups = Counter(
        (
            "+".join(row["declared"]) or "none",
            "+".join(row["confirmed"]) or "none",
            row["verdict"],
        )
        for row in confirmations
    )
    return {
        "schema_version": "1.0.0",
        "corpus": corpus_identity(corpus),
        "pipeline": pipeline_identity(),
        "analyzers": {
            "whitakers": package_version("whitakers-words"),
            "collatinus": package_version("pycollatinus"),
        },
        "counts": {
            "texts": texts,
            "tokens": len(verdicts),
            "provenance_mismatch": len(provenance),
            "by_verdict": dict(sorted(Counter(v.verdict for v in verdicts).items())),
        },
        "confirmations_sha256": root,
        "confirmation_groups": [
            {
                "declared": declared,
                "confirmed": confirmed,
                "verdict": verdict,
                "tokens": count,
            }
            for (declared, confirmed, verdict), count in sorted(groups.items())
        ],
        "mismatches": provenance,
        **({"confirmations": confirmations} if include_confirmations else {}),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--attestation", type=Path)
    parser.add_argument("--attestation-details", action="store_true")
    parser.add_argument("corpus", type=Path)
    try:
        args = parser.parse_args(argv[1:])
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 2
    corpus = args.corpus
    texts, verdicts, provenance, confirmations = run(corpus)
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

    if args.attestation:
        attestation = confirmation_attestation(
            corpus,
            texts,
            verdicts,
            provenance,
            confirmations,
            include_confirmations=args.attestation_details,
        )
        args.attestation.parent.mkdir(parents=True, exist_ok=True)
        args.attestation.write_text(
            json.dumps(attestation, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

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
    ok = "OK" if not (args.strict and provenance) else "FAIL"
    print(
        f"VERDICT {ok} texts={texts} tokens={len(verdicts)} {subject} [{breakdown}] "
        f"queue={len(queue)} provenance_mismatch={len(provenance)}"
    )
    return 1 if (args.strict and provenance) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
