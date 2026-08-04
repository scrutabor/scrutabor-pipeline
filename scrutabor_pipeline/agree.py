"""The source-agreement rule: is the corpus's editorial analysis among the
candidates an independent analyzer proposes for the same form?

Verdicts:
- AGREE            analyzer proposes our exact reading under our lemma
- AGREE_FORM_ONLY  our reading is among the candidates, but the lemma
                   identity could not be established (lemma unknown to the
                   analyzer, or known under a different entry)
- DIVERGE          the analyzer knows the form but proposes no candidate
                   matching our reading — review queue material
- FORM_ABSENT      the analyzer does not know the form at all
"""

from dataclasses import dataclass

from .whitakers import Candidate, candidates, lemma_candidates

# Recorded classification rulings (corpus SCHEMA.md, TERMINOLOGY decisions):
# our part of speech on the left may match these analyzer parts of speech.
POS_RULINGS: dict[str, set[str]] = {
    # sicut is tagged conj in the corpus; several dictionaries head it as
    # an adverb. Whitaker's proposes both, so this ruling is usually moot,
    # but it is recorded so a CONJ-less candidate set stays an expected
    # divergence, not a silent one.
    "conj": {"conj", "adv"},
    # amen (and other indeclinable Hebrew loans) are intj in the corpus;
    # Whitaker's classes them as adverbs.
    "intj": {"intj", "adv"},
    # prohibitive ne is adv in the corpus (a reviewed ruling); Whitaker's
    # heads it as conj/adv.
    "adv": {"adv", "conj"},
}

# Lemma spellings the analyzer dictionaries as separate entries: our lemma
# on the left, every analyzer entry that IS the same word on the right.
LEMMA_ALIASES: dict[str, tuple[str, ...]] = {
    "ab": ("a", "ab"),  # Whitaker's carries a and ab as two entries
}

# Lemmas the analyzer's dictionary does not carry, each with the reason.
# An absent form under one of these is expected, not a finding.
EXPECTED_ABSENT: dict[str, str] = {
    "Maria": "proper name (Hebrew), not in the analyzer dictionary",
    "Michael": "proper name (Hebrew), not in the analyzer dictionary",
    "Ioannes": "proper name (Hebrew), not in the analyzer dictionary",
    "Iesus": "proper name (Hebrew), not in the analyzer dictionary",
}

# Features the corpus stores that the comparison checks when the analyzer
# offers an opinion on them. decl/conj are checked against the lexeme
# category separately; `governs` is editorial-only (not exposed by the port).
COMPARED = ("case", "number", "gender", "person", "tense", "mood", "voice", "degree")


@dataclass
class Verdict:
    token_ref: str  # "<text-id>.<word-id>"
    verdict: str
    detail: str = ""


def _features_match(ours: dict, candidate: Candidate) -> bool:
    theirs = candidate.feature_dict()
    for key in COMPARED:
        our_value = ours.get(key)
        their_value = theirs.get(key)
        if our_value is None or their_value is None:
            continue  # one side has no opinion — compatible
        if key == "voice" and our_value == "dep":
            # A deponent's form IS passive; the analyzer says pass, we say
            # dep about the lemma. Same claim, two vocabularies.
            if their_value != "pass":
                return False
            continue
        if our_value != their_value:
            return False
    return True


def _pos_match(our_pos: str, candidate_pos: str) -> bool:
    return candidate_pos == our_pos or candidate_pos in POS_RULINGS.get(our_pos, set())


def compare(text_id: str, word: dict) -> Verdict:
    ref = f"{text_id}.{word['id']}"
    ours = dict(word["morph"])
    our_pos = ours.pop("pos")
    lemma = word["lemma"]

    cands = candidates(word["form"])
    if not cands:
        if lemma in EXPECTED_ABSENT:
            return Verdict(ref, "FORM_ABSENT", f"expected: {EXPECTED_ABSENT[lemma]}")
        return Verdict(ref, "FORM_ABSENT", f"form {word['form']!r} unknown to the analyzer")

    matching = [c for c in cands if _pos_match(our_pos, c.pos) and _features_match(ours, c)]
    if not matching:
        proposals = sorted({f"{c.pos}:{c.feature_dict()}" for c in cands})
        return Verdict(ref, "DIVERGE", f"ours={our_pos}:{ours} analyzer={proposals[:6]}")

    ids = {
        c.lexeme_id
        for spelling in LEMMA_ALIASES.get(lemma, (lemma,))
        for c in lemma_candidates(spelling)
        if _pos_match(our_pos, c.pos)
    }
    if ids and any(c.lexeme_id in ids for c in matching):
        return Verdict(ref, "AGREE")
    return Verdict(
        ref,
        "AGREE_FORM_ONLY",
        f"reading matches, lemma {lemma!r} not linkable to the analyzer entry",
    )
