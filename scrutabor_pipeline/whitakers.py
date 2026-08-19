"""Adapter: Whitaker's Words output -> candidates in the corpus morph space.

The corpus morph enums are the target vocabulary (see the corpus repo's
SCHEMA.md); every candidate an analyzer proposes is translated into it so
agreement can be checked mechanically.
"""

from dataclasses import dataclass, field
from functools import lru_cache

from whitakers_words.parser import Parser

from .normalize import analyzer_query, whitakers_query

POS = {
    # Participles arrive under this key too, and there is no VPAR entry
    # because a LEXEME is never VPAR: that word type belongs to the
    # INFLECTION, and no stem or unique in the port's data carries it. What
    # a VPAR inflection does carry is case, number, gender, tense and voice
    # and no Mood, so the candidate's mood stays open and matches the
    # corpus's mood "part", while a finite candidate (whose mood IS stated)
    # cannot.
    "V": "verb",
    "N": "noun",
    "ADJ": "adj",
    # Whitaker's separates numerals from adjectives; the corpus tags
    # declining ordinals (unus, tertius) as adj.
    "NUM": "adj",
    "PRON": "pron",
    "ADV": "adv",
    "CONJ": "conj",
    "PREP": "prep",
    "INTERJ": "intj",
}

CASE = {
    "NOM": "nom",
    "GEN": "gen",
    "DAT": "dat",
    "ACC": "acc",
    "ABL": "abl",
    "VOC": "voc",
    "LOC": "loc",  # not a corpus case; a LOC-only candidate never matches
}

NUMBER = {"S": "sg", "P": "pl"}
GENDER = {"M": "m", "F": "f", "N": "n"}  # C (common) and X (unknown) -> wildcard
TENSE = {
    "PRES": "pres",
    "IMPF": "impf",
    "FUT": "fut",
    "PERF": "perf",
    "PLUP": "plup",
    "FUTP": "futperf",
}
MOOD = {"IND": "ind", "SUB": "subj", "IMP": "imp", "INF": "inf"}
VOICE = {"ACTIVE": "act", "PASSIVE": "pass"}
DEGREE = {"COMP": "comp", "SUPER": "sup"}  # POS (positive) -> absent, like the corpus


@dataclass(frozen=True)
class Candidate:
    """One analyzer reading of a form, in corpus vocabulary. A feature value
    of None means the analyzer left it open (wildcard)."""

    lexeme_id: int
    pos: str
    features: tuple = field(default_factory=tuple)  # sorted (key, value) pairs

    def feature_dict(self) -> dict:
        return dict(self.features)


@lru_cache(maxsize=1)
def _parser() -> Parser:
    # The port defaults to a frequency floor of "C" (common words only),
    # which silently drops the ecclesiastical vocabulary a liturgical corpus
    # lives on (peccator, temptatio, omnipotens, archangelus, sanctifico all
    # carry "lesser/uncommon" codes). "E" admits them; extra candidates can
    # never break set-membership agreement, only enable it.
    return Parser(frequency="E")


def _map_features(raw: dict) -> dict:
    out: dict = {}
    for key, value in raw.items():
        name = getattr(value, "name", str(value))
        if key == "Case":
            out["case"] = CASE.get(name)
        elif key == "Number":
            out["number"] = NUMBER.get(name)  # X -> None wildcard
        elif key == "Gender":
            out["gender"] = GENDER.get(name)  # C/X -> None wildcard
        elif key == "Tense":
            out["tense"] = TENSE.get(name)
        elif key == "Mood":
            out["mood"] = MOOD.get(name)
        elif key == "Voice":
            out["voice"] = VOICE.get(name)
        elif key == "Person":
            person = getattr(value, "value", None)
            out["person"] = person if person in (1, 2, 3) else None
        elif key == "Degree":
            out["degree"] = DEGREE.get(name)  # POS -> None (positive unmarked)
    return out


def candidates(form: str) -> list[Candidate]:
    """All analyzer readings of a display form, translated. Empty list means
    the analyzer does not know the form at all.

    Asked in BOTH spellings of the glide, because this analyzer is not
    consistent with itself: its dictionary heads the consonant as j (jubeo,
    majestas, Jesus — the i-form returns nothing), while its pronoun
    inflections are generated in i (eius hits, ejus does not). No pair of
    Latin words is distinguished by i against j — it is one sound in two
    notations — so the union is the analyzer's real answer, and asking only
    one way silently mutes it. It was muted on 41 tokens of this corpus
    until 2026-08-06.
    """
    queries = {analyzer_query(form), whitakers_query(form)}
    out: list[Candidate] = []
    for parsed_form in [f for q in sorted(queries) for f in _parser().parse(q).forms]:
        for analysis in parsed_form.analyses.values():
            word_type = analysis.lexeme.wordType.name
            pos = POS.get(word_type)
            if pos is None:
                continue
            for inflection in analysis.inflections:
                mapped = _map_features(inflection.features)
                out.append(
                    Candidate(
                        lexeme_id=analysis.lexeme.id,
                        pos=pos,
                        features=tuple(sorted(mapped.items())),
                    )
                )
            if not analysis.inflections:
                out.append(Candidate(lexeme_id=analysis.lexeme.id, pos=pos))
    return out


def lemma_candidates(lemma: str) -> list[Candidate]:
    """Readings of the corpus lemma string itself — the identity link
    between our headword and the analyzer's dictionary entry (a lemma is
    always one of its own forms: nom sg, 1sg pres, the bare particle)."""
    return candidates(lemma)
