# scrutabor-pipeline

Verification and build machinery for the
[Scrutabor](https://github.com/scrutabor/scrutabor-app) corpus — the
mechanical half of the corpus quality doctrine: *the system must know what
it doesn't know.*

## Source agreement

Every analysis in
[scrutabor-corpus](https://github.com/scrutabor/scrutabor-corpus) names its
sources and review state. This pipeline checks the corpus's editorial
morphology against two independent analyzers — **Whitaker's Words** (the
[Python port](https://github.com/blagae/whitakers_words), pinned, run with
a frequency floor that admits ecclesiastical vocabulary) and **Collatinus**
(via [pycollatinus](https://pypi.org/project/pycollatinus/), revived for
modern Python by a two-line compatibility shim). Each analyzer votes
separately on every token; agreement means the corpus reading appears
among the analyzer's candidates *under the same dictionary entry*.

Liturgical orthography (accents, *j*, ligatures, diaeresis) is normalized
to dictionary spellings mechanically. Everything the analyzers see
differently is recorded as data, never worked around in code: spelling
divergences (*quotidiánus* → *cotidianus*), classification rulings
(*sicut* as conjunction, *amen* as interjection), lemma aliases (*a/ab*
as two Whitaker's entries, *tecum* as its own Collatinus entry), and the
two vocabularies of deponency (Whitaker's reports the passive *form*,
Collatinus the active *meaning*).

## Usage

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m scrutabor_pipeline.agreement path/to/scrutabor-corpus
```

### Reading the report

The last line is the verdict, and it names everything it checked:

```
VERDICT OK texts=4 tokens=167 agree=167 agree_form_only=0 diverge=0 form_absent=0 [collatinus=5 whitakers+collatinus=162] queue=0
```

- **`agree`** — tokens whose corpus reading at least one analyzer proposes
  under the same dictionary entry, with no analyzer objecting. The
  bracketed breakdown says which analyzers confirmed how many tokens.
- **`diverge`** — *the number to watch*: an analyzer knows the form but
  proposes no reading matching the corpus. Each divergence is printed with
  the corpus reading and every analyzer proposal side by side, and written
  to `review-queue.json` for adjudication.
- **`agree_form_only`** — the reading matches, but the corpus lemma could
  not be linked to the analyzer's dictionary entry. Usually means a lemma
  alias should be recorded (that is how *a/ab* earned its entry).
- **`form_absent`** — no analyzer knows the form. Expected absences carry
  a recorded reason and print as `expected: …`; an absence *without* one
  is a gap to investigate or a new expected entry to record.
- **`queue`** — entries written to `review-queue.json` (divergences only).

Every token that is not a plain agreement is printed line by line above
the verdict, so a healthy run prints nothing but the verdict (or
`expected:` absences). Exit codes: `0` — the report ran and named its
counts, even when divergences exist (the report is a measurement; gating
happens where findings are adjudicated); `2` — usage error or zero tokens
(a report that checked nothing must not pass).

## Development

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

Module map:

| module | role |
|---|---|
| `normalize.py` | liturgical display forms → dictionary spellings |
| `whitakers.py` | Whitaker's Words adapter → candidates in corpus vocabulary |
| `collatinus.py` | Collatinus adapter (French morphology → corpus vocabulary) |
| `compat.py` | the shim that revives pycollatinus on Python ≥ 3.10 |
| `agree.py` | per-analyzer votes, combined verdicts, recorded rulings |
| `agreement.py` | the report runner and review-queue writer |

Extending the recorded knowledge (all in `agree.py` / `normalize.py`,
always with a reason in the adjacent comment):

- a liturgical spelling the dictionaries head differently →
  `SPELLING_PREFIXES` (prefix rewrite, so every inflected form maps);
- a part-of-speech classification the corpus rules differently than the
  dictionaries → `POS_RULINGS`;
- a word one analyzer dictionaries as a separate or fused entry →
  `LEMMA_ALIASES`;
- a word no analyzer carries → `EXPECTED_ABSENT`, with the reason that
  will be printed.

A new analyzer is an adapter module returning candidates in the corpus
morph vocabulary plus a vote function in `agree.py`; nothing else changes.
Tests must include negative cases — a wrong case or a false voice claim
has to be *seen* caught (`tests/test_agree.py` keeps the proof).

## License

[AGPL-3.0](LICENSE). The corpus data this pipeline verifies is
CC BY-SA 4.0 in its own repository.
