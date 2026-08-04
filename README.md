# scrutabor-pipeline

Verification and build machinery for the
[Scrutabor](https://github.com/scrutabor/scrutabor-app) corpus — the
mechanical half of the corpus quality doctrine: *the system must know what
it doesn't know.*

## Source agreement

Every analysis in
[scrutabor-corpus](https://github.com/scrutabor/scrutabor-corpus) names its
sources and review state. This pipeline checks the corpus's editorial
morphology against independent analyzers and classifies every token:

- **AGREE** — the analyzer proposes exactly the corpus reading, under the
  same dictionary entry;
- **DIVERGE** — the analyzer knows the form but proposes no matching
  reading: review-queue material;
- **FORM_ABSENT** — the analyzer does not know the form (expected for the
  Hebrew proper names of the prayers).

Liturgical orthography (accents, *j*, ligatures, diaeresis) is normalized
to dictionary spellings mechanically, including the recorded divergences
(*quotidiánus* → *cotidianus*, *tentátio* → *temptatio*); recorded
classification rulings (e.g. *sicut* as conjunction) and lemma aliases
(*a/ab*) are applied as data, so expected divergences never masquerade as
findings.

The first analyzer is Whitaker's Words (the
[Python port](https://github.com/blagae/whitakers_words), pinned; run with
a frequency floor that admits ecclesiastical vocabulary). Collatinus is a
planned second vote; its Python port is unmaintained, so integration will
consume its data files directly.

## Usage

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m scrutabor_pipeline.agreement path/to/scrutabor-corpus
```

The run prints a verdict that names its subject (texts, tokens, counts per
classification) and writes `review-queue.json` with every divergence.

## Development

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

## License

[AGPL-3.0](LICENSE). The corpus data this pipeline verifies is
CC BY-SA 4.0 in its own repository.
