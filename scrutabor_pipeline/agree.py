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
- AGREE_RULED      as AGREE, but one analyzer's contradiction was set aside
                   by a recorded ruling (FEATURE_RULINGS) — counted apart so
                   an adjudicated token never hides inside a clean number
- AGREE_FORM_ONLY  no contradiction, only form-level matches
- FORM_ABSENT      no analyzer knows the form
- EDITORIAL_ONLY   the only analyzer that knows the form was set aside by a
                   ruling, so nothing machine-checkable remains — the parse
                   rests on the edition alone and says so in its provenance
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
    # Homograph discriminators (corpus SCHEMA.md): the key carries the part of
    # speech, the analyzers are asked about the word itself.
    "hic_adverbium": ("hic",),
    "memini": ("memini", "memento"),  # Collatinus heads the imperative itself
    # Collatinus heads the adjective under its archaic nominative saluos,
    # which the u/v fold of salvus (saluus) cannot reach. Both analyzers
    # do read the word; only the spelling of the head differs.
    "salvus": ("salvus", "salvos"),
}

# Lemmas no analyzer carries, each with the reason. An absent form under one
# of these is expected, not a finding. (Currently empty: Collatinus knows
# even the Hebrew proper names of the prayers.)
EXPECTED_ABSENT: dict[str, str] = {
    # Martyrs of the Canon whose names are in neither analyzer's lexicon. The
    # genitive of each is secure from the chain of genitives it stands in;
    # only the dictionaries are silent.
    "Cletus": "pope and martyr of the Communicantes; in neither lexicon",
    "Cosmas": "martyr of the Communicantes; in neither lexicon",
    "Damianus": "martyr of the Communicantes; in neither lexicon",
}

# Contradictions already adjudicated: the named analyzer is demonstrably
# wrong about this form, or models it differently from us in a way we have
# reasoned through. Keyed "<lemma>:<form>" on the corpus's own spelling.
#
# A ruling makes that ONE analyzer abstain — it never invents a
# confirmation. If the other analyzer does not confirm, the token still
# does not reach AGREE, and the report counts ruled tokens separately so
# they can never hide inside a clean number. Every entry carries the
# reason it was accepted; that reason is the whole value of the mechanism.
FEATURE_RULINGS: dict[str, dict[str, str]] = {
    "quaeso:quǽsumus": {
        "collatinus": (
            "reads the fossilised parenthetical as its own lemma and tags it "
            "3rd singular; the form is the 1st plural of quaeso, as Whitaker's "
            "and every grammar have it"
        )
    },
    "vos:vobíscum": {
        "collatinus": (
            "dictionaries the fused vobis+cum as one lemma and tags it "
            "singular; the enclitic attaches to a plural ablative (cf. the "
            "tu/tecum alias above)"
        )
    },
    "vos:vestri": {
        "collatinus": (
            "links the form only to the possessive vester; vestri is also the "
            "genitive of vos, which is what misereor governs here — Whitaker's "
            "confirms it"
        )
    },
    # --- the Canon ---
    "refrigerium:refrigérii": {
        "whitakers": (
            "carries THIS ENTRY with the contracted genitive singular alone (refrigeri) and "
            "so reads the uncontracted refrigérii as a locative. Not a rule about -ium "
            "nouns: the same analyzer reads Evangélii as a genitive singular. Lewis and "
            "Short head the noun refrigerium, ii, three coordinate genitives leave a "
            "locative no room, and Collatinus confirms the genitive"
        )
    },
    "clemens:clementíssime": {
        "whitakers": (
            "offers only the superlative ADVERB for this form; clementíssime Pater is the "
            "vocative agreeing with Pater, which Collatinus heads and confirms"
        )
    },
    "martyr:Mártyrum": {
        "whitakers": (
            "returns genitive SINGULAR for mártyrum, a number the form cannot carry (the "
            "genitive singular is mártyris) — a porting artefact; Collatinus gives the "
            "genitive plural the series of plural genitives requires"
        )
    },
    "memini:Meménto": {
        "whitakers": (
            "tags the form present; meménto is the FUTURE imperative, and the only imperative "
            "memini has. Collatinus agrees on the tense under its own lemma. Omitting the "
            "tense would have satisfied both analyzers by claiming less than is known"
        )
    },
    "Linus:Lini": {
        "whitakers": (
            "carries no pope Linus — only linum (flax) and lino — and so reads the name as a "
            "neuter noun; Collatinus heads Linus and confirms the genitive"
        )
    },
    "Clemens:Cleméntis": {
        "whitakers": (
            "carries only the adjective clemens, not the pope's name; Collatinus confirms the "
            "genitive of the name"
        )
    },
    "Perpetua:Perpétua": {
        "whitakers": ("carries no martyr Perpetua and reads the name as the adjective perpetuus"),
        "collatinus": (
            "likewise heads only perpetuus/perpetuum; neither lexicon carries her, so the "
            "parse stands on the edition alone"
        ),
    },
    "fio:fíeri": {
        "collatinus": (
            "reads the present infinitive as an imperative; fíeri is the infinitive of fio, "
            "as its own dictionary head (fio, fíeri, factus sum) and Whitaker's have it, and "
            "fio has no passive imperative"
        )
    },
    "sanctificator:sanctificátor": {
        "whitakers": (
            "carries no agent noun sanctificator and reads the -tor ending as the archaic "
            "future passive imperative of sanctifico; the word is the Christian-Latin noun "
            "sanctificátor, sanctificatóris, which Collatinus heads and confirms in the vocative"
        )
    },
    "filius:Fílii": {
        "whitakers": (
            "carries THIS ENTRY with the contracted genitive singular alone (fili) and "
            "so reads filii as plural or locative. Not a rule about -ius nouns: the "
            "same analyzer reads Evangélii as a genitive singular, and does not carry "
            "Cornelii or Laurentii at all. The uncontracted filii is the genitive "
            "throughout the Vulgate and the liturgical books, the genitive chains of "
            "the Canon admit nothing else, and Collatinus confirms it"
        )
    },
}

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

    # An adjudicated contradiction abstains instead of counting against us,
    # and the token is reported as ruled rather than as plain agreement.
    rulings = FEATURE_RULINGS.get(f"{word['lemma']}:{word['form']}", {})
    ruled = [
        f"{name} set aside: {reason}"
        for name, reason in rulings.items()
        if votes.get(name, ("", ""))[0] == "CONTRADICTS"
    ]
    for name in rulings:
        if votes.get(name, ("", ""))[0] == "CONTRADICTS":
            votes[name] = ("ABSTAINS", "")

    contradictions = [f"{d}" for v, d in votes.values() if v == "CONTRADICTS"]
    if contradictions:
        return Verdict(
            ref, "DIVERGE", detail=f"ours={our_pos}:{ours} | " + " | ".join(contradictions)
        )

    confirming = [name for name, (v, _) in votes.items() if v == "CONFIRMS"]
    if confirming:
        if ruled:
            return Verdict(
                ref, "AGREE_RULED", sources="+".join(confirming), detail="; ".join(ruled)
            )
        return Verdict(ref, "AGREE", sources="+".join(confirming))

    form_matches = [d for v, d in votes.values() if v == "FORM_MATCH"]
    if form_matches:
        return Verdict(ref, "AGREE_FORM_ONLY", detail="; ".join(form_matches))

    # A ruling set the only opinion aside: say that, rather than claim the
    # form is unknown — it is known, and we judged it wrong.
    if ruled:
        return Verdict(
            ref,
            "EDITORIAL_ONLY",
            detail=f"no analyzer confirms {word['form']!r} — " + "; ".join(ruled),
        )
    lemma = word["lemma"]
    if lemma in EXPECTED_ABSENT:
        return Verdict(ref, "FORM_ABSENT", detail=f"expected: {EXPECTED_ABSENT[lemma]}")
    return Verdict(ref, "FORM_ABSENT", detail=f"form {word['form']!r} unknown to every analyzer")
