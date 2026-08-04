"""Adapter: Collatinus (pycollatinus) output -> candidates in the corpus
morph space.

Collatinus reports morphology as French prose ("2ème singulier subjonctif
présent actif") and identifies lemmas by string in classical u-orthography
(aueo, not aveo), sometimes with homonym digits. Both are folded into the
corpus vocabulary here. Nouns carry no gender in its morph strings (gender
is lexeme-level), which the comparison treats as an open feature.
"""

from dataclasses import dataclass, field
from functools import lru_cache

from . import compat
from .normalize import analyzer_query

# French morphological vocabulary -> corpus enums. Two-word tenses are
# matched before their one-word prefixes.
PHRASES = [
    ("plus-que-parfait", ("tense", "plup")),
    ("futur antérieur", ("tense", "futperf")),
]

TOKENS = {
    "nominatif": ("case", "nom"),
    "génitif": ("case", "gen"),
    "datif": ("case", "dat"),
    "accusatif": ("case", "acc"),
    "ablatif": ("case", "abl"),
    "vocatif": ("case", "voc"),
    "locatif": ("case", "loc"),  # not a corpus case; never matches
    "singulier": ("number", "sg"),
    "pluriel": ("number", "pl"),
    "masculin": ("gender", "m"),
    "féminin": ("gender", "f"),
    "neutre": ("gender", "n"),
    "1ère": ("person", 1),
    "2ème": ("person", 2),
    "3ème": ("person", 3),
    "présent": ("tense", "pres"),
    "imparfait": ("tense", "impf"),
    "futur": ("tense", "fut"),
    "parfait": ("tense", "perf"),
    "indicatif": ("mood", "ind"),
    "subjonctif": ("mood", "subj"),
    "impératif": ("mood", "imp"),
    "infinitif": ("mood", "inf"),
    "actif": ("voice", "act"),
    "passif": ("voice", "pass"),
    "comparatif": ("degree", "comp"),
    "superlatif": ("degree", "sup"),
}


@dataclass(frozen=True)
class Candidate:
    """One Collatinus reading: the lemma folded for comparison plus the
    features its morph string states. Absent features are open."""

    lemma: str
    features: tuple = field(default_factory=tuple)

    def feature_dict(self) -> dict:
        return dict(self.features)


def fold_lemma(lemma: str) -> str:
    """Fold a lemma string (ours or Collatinus's) for identity comparison:
    dictionary spelling, u for v, no homonym digits."""
    return analyzer_query(lemma).replace("v", "u").rstrip("0123456789")


def parse_morph(morph: str) -> dict:
    features: dict = {}
    text = morph
    for phrase, (key, value) in PHRASES:
        if phrase in text:
            features[key] = value
            text = text.replace(phrase, " ")
    for token in text.split():
        mapped = TOKENS.get(token)
        if mapped:
            features[mapped[0]] = mapped[1]
    return features


@lru_cache(maxsize=1)
def _lemmatiseur():
    compat.apply()
    from pycollatinus import Lemmatiseur

    return Lemmatiseur()


def candidates(form: str) -> list[Candidate]:
    """All Collatinus readings of a display form, translated. Empty list:
    the analyzer does not know the form."""
    results = _lemmatiseur().lemmatise(analyzer_query(form))
    out = []
    for reading in results:
        features = parse_morph(reading.get("morph") or "")
        out.append(
            Candidate(
                lemma=fold_lemma(reading.get("lemma") or ""),
                features=tuple(sorted(features.items())),
            )
        )
    return out
