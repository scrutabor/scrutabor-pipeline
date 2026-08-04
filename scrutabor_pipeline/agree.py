"""The source-agreement rule: is the corpus's editorial analysis among the
candidates each independent analyzer proposes for the same form?

Each analyzer votes separately:
- CONFIRMS      proposes our exact reading under our dictionary entry
- FORM_MATCH    proposes our reading, but under an entry that could not be
                linked to our lemma
- CONTRADICTS   knows the form but proposes no reading matching ours
- ABSENT        does not know the form

Combined verdict for a token:
- DIVERGE          any analyzer contradicts — review queue material
- AGREE            no contradiction, at least one analyzer confirms
                   (detail names which)
- AGREE_FORM_ONLY  no contradiction, only form-level matches
- FORM_ABSENT      no analyzer knows the form
"""

from dataclasses import dataclass

from . import collatinus, whitakers

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

# Lemma spellings the analyzers dictionary as separate or fused entries:
# our lemma on the left, every analyzer entry that IS the same word on the
# right.
LEMMA_ALIASES: dict[str, tuple[str, ...]] = {
    "ab": ("a", "ab"),  # Whitaker's carries a and ab as two entries
    "tu": ("tu", "tecum"),  # Collatinus dictionaries the fused tecum itself
}

# Lemmas no analyzer carries, each with the reason. An absent form under one
# of these is expected, not a finding. (Currently empty: Collatinus knows
# even the Hebrew proper names of the prayers.)
EXPECTED_ABSENT: dict[str, str] = {}

# Features the corpus stores that the comparison checks when an analyzer
# offers an opinion on them. decl/conj and `governs` are editorial-level
# (not exposed comparably by the adapters).
COMPARED = ("case", "number", "gender", "person", "tense", "mood", "voice", "degree")


@dataclass
class Verdict:
    token_ref: str  # "<text-id>.<word-id>"
    verdict: str
    sources: str = ""  # analyzers that confirmed, "+"-joined
    detail: str = ""


def _features_match(ours: dict, theirs: dict) -> bool:
    for key in COMPARED:
        our_value = ours.get(key)
        their_value = theirs.get(key)
        if our_value is None or their_value is None:
            continue  # one side has no opinion — compatible
        if key == "voice" and our_value == "dep":
            # Deponency is a lemma-level fact the analyzers vocabularize
            # differently: Whitaker's reports the passive FORM, Collatinus
            # the active MEANING. Lemma identity is checked separately, so
            # the voice tag itself is not compared for deponents.
            continue
        if our_value != their_value:
            return False
    return True


def _pos_match(our_pos: str, candidate_pos: str) -> bool:
    return candidate_pos == our_pos or candidate_pos in POS_RULINGS.get(our_pos, set())


def _whitakers_vote(word: dict, our_pos: str, ours: dict) -> tuple[str, str]:
    cands = whitakers.candidates(word["form"])
    if not cands:
        return "ABSENT", ""
    matching = [
        c for c in cands if _pos_match(our_pos, c.pos) and _features_match(ours, c.feature_dict())
    ]
    if not matching:
        proposals = sorted({f"{c.pos}:{c.feature_dict()}" for c in cands})
        return "CONTRADICTS", f"whitakers proposes {proposals[:6]}"
    ids = {
        c.lexeme_id
        for spelling in LEMMA_ALIASES.get(word["lemma"], (word["lemma"],))
        for c in whitakers.lemma_candidates(spelling)
        if _pos_match(our_pos, c.pos)
    }
    if ids and any(c.lexeme_id in ids for c in matching):
        return "CONFIRMS", ""
    return "FORM_MATCH", f"whitakers cannot link lemma {word['lemma']!r}"


def _collatinus_vote(word: dict, our_pos: str, ours: dict) -> tuple[str, str]:
    cands = collatinus.candidates(word["form"])
    if not cands:
        return "ABSENT", ""
    matching = [c for c in cands if _features_match(ours, c.feature_dict())]
    if not matching:
        proposals = sorted({f"{c.lemma}:{c.feature_dict()}" for c in cands})
        return "CONTRADICTS", f"collatinus proposes {proposals[:6]}"
    accepted = {
        collatinus.fold_lemma(spelling)
        for spelling in LEMMA_ALIASES.get(word["lemma"], (word["lemma"],))
    }
    if any(c.lemma in accepted for c in matching):
        return "CONFIRMS", ""
    return "FORM_MATCH", f"collatinus reads it under {sorted({c.lemma for c in matching})[:4]}"


def compare(text_id: str, word: dict) -> Verdict:
    ref = f"{text_id}.{word['id']}"
    ours = dict(word["morph"])
    our_pos = ours.pop("pos")

    votes = {
        "whitakers": _whitakers_vote(word, our_pos, ours),
        "collatinus": _collatinus_vote(word, our_pos, ours),
    }

    contradictions = [f"{d}" for v, d in votes.values() if v == "CONTRADICTS"]
    if contradictions:
        return Verdict(ref, "DIVERGE", detail=f"ours={our_pos}:{ours} | " + " | ".join(contradictions))

    confirming = [name for name, (v, _) in votes.items() if v == "CONFIRMS"]
    if confirming:
        return Verdict(ref, "AGREE", sources="+".join(confirming))

    form_matches = [d for v, d in votes.values() if v == "FORM_MATCH"]
    if form_matches:
        return Verdict(ref, "AGREE_FORM_ONLY", detail="; ".join(form_matches))

    lemma = word["lemma"]
    if lemma in EXPECTED_ABSENT:
        return Verdict(ref, "FORM_ABSENT", detail=f"expected: {EXPECTED_ABSENT[lemma]}")
    return Verdict(ref, "FORM_ABSENT", detail=f"form {word['form']!r} unknown to every analyzer")
