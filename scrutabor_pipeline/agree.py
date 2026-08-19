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
    # The Advent IV gospel's `in libro`, discriminated from liber the adjective
    # (free). Without the alias the underscore key reached Whitaker's as a
    # word, and the whole comparison raised rather than returning a verdict --
    # so the agreement report and the review queue could not be produced at
    # all from 2026-08-18, the day that text landed.
    "liber_volumen": ("liber",),
    # Collatinus dictionaries the fused id+ipsum as one lemma (as it does
    # tecum, three lines up); the corpus lemmatizes the pronoun under idem
    # and lets the fusion be the form's business.
    "idem": ("idem", "idipsum"),
    "memini": ("memini", "memento"),  # Collatinus heads the imperative itself
    # Collatinus heads the adjective under its archaic nominative saluos,
    # which the u/v fold of salvus (saluus) cannot reach. Both analyzers
    # do read the word; only the spelling of the head differs.
    "salvus": ("salvus", "salvos"),
}


def link_spellings(lemma: str) -> tuple[str, ...]:
    """The dictionary spellings a lemma may be linked under.

    A discriminated key (liber_volumen) is the corpus's own notation, not a
    Latin word, and SCHEMA.md requires it to carry an alias above. When the
    alias is missing, the honest answer is NO spellings: the analyzers then
    fail to link the lemma and the verdict says so — instead of the raw
    underscore key reaching Whitaker's as a word and the whole report dying
    on it, which is how the machine sat unrunnable from 2026-08-18 while
    thirty texts landed, and how it would have died again on the next such
    key with only the one alias added.
    """
    if lemma in LEMMA_ALIASES:
        return LEMMA_ALIASES[lemma]
    if "_" in lemma:
        return ()
    return (lemma,)


# Lemmas no analyzer carries, each with the reason. An absent form under one
# of these is expected, not a finding.
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
    "pressura:pressúra": {
        "whitakers": (
            "misclassifies the nominative singular noun pressura as a verbal form of presso; "
            "Collatinus confirms the noun, and the Vulgate text and surrounding syntax require "
            "it as the subject of erit"
        )
    },
    "Israel:Israël": {
        "whitakers": (
            "treats the indeclinable proper name as nominative or vocative only; the corpus "
            "reads it in the case its own syntax requires — the object of rédimet in the "
            "psalm, and plebis tuæ Israël standing in apposition to a genitive in the Advent "
            "alleluia — while Collatinus leaves the case open. The reason once argued only "
            "the accusative and the ruling outgrew it; it is a rule about the analyzer's "
            "closed case list, not about one verse"
        )
    },
    "consilium:consílii": {
        "whitakers": (
            "offers only a locative for the uncontracted form; consílii is the genitive "
            "singular required by boni and magni in the two litany invocations, and "
            "Collatinus confirms it"
        )
    },
    "oboediens:obœdientíssime": {
        "whitakers": (
            "offers only an adverb, while the form is the masculine vocative superlative "
            "agreeing with Iesu; Collatinus confirms the adjective"
        )
    },
    "zelator:zelátor": {
        "whitakers": (
            "has no agent noun zelator and misreads its vocative as a future passive "
            "imperative; Collatinus confirms the noun used in apposition to Iesu"
        )
    },
    # --- the Advent divergences, adjudicated 2026-08-19 ---
    # Nineteen tokens sat in the review queue from the day the machine came
    # back up. Read against the grammar and the analyzers' live output, every
    # one is a case where the edition is right and a dictionary is short.
    "meus:meus": {
        "whitakers": (
            "offers only the nominative; Deus meus is the Psalter's address (Ps 21:2 and "
            "throughout), the possessive standing in the vocative beside the "
            "nominative-for-vocative Deus, where the classical paradigm's mi never appears "
            "in these books"
        ),
        "collatinus": (
            "the same: nominative alone, the classical mi expected for the vocative. The "
            "form of address the liturgy actually prints is meus, at every one of its "
            "occurrences here"
        ),
    },
    "Ierusalem:Ierúsalem": {
        "whitakers": (
            "heads the city neuter (the Hierosolyma, -orum tradition) and contradicts the "
            "feminine; the indeclinable singular name is feminine in the scriptures' own "
            "concord — quæ occídis prophétas (Mt 23:37) — and in the vocative here "
            "(Ierúsalem, surge)"
        )
    },
    "solatium:solátii": {
        "whitakers": (
            "the contracted-genitive defect of refrigérii and consílii above, at another "
            "-ium noun: it carries the entry with the contracted genitive alone and reads "
            "the uncontracted solátii as a locative. Deus patiéntiæ et solátii is a pair "
            "of coordinate genitives, and Collatinus confirms the second"
        )
    },
    "imperium:impérii": {
        "whitakers": (
            "the same contracted-genitive defect: anno quintodécimo impérii Tibérii "
            "Cǽsaris is a chain of genitives dating the year, and a locative has no place "
            "in it. Collatinus confirms the genitive"
        )
    },
    "Tiberius:Tibérii": {
        "whitakers": (
            "the same defect on the emperor's name: it reads the uncontracted genitive as "
            "a locative or a plural. One Tiberius, whose reign the verse dates; Collatinus "
            "confirms the genitive singular"
        )
    },
    "exeo:exístis": {
        "whitakers": (
            "reads the form as a present of exsisto; exístis in Mt 11:7-9 (quid exístis "
            "in desértum vidére) is the contracted perfect of exeo — exi(v)istis, 'what "
            "went ye out to see' — as the received rendering of every age has it, and "
            "Collatinus confirms exactly that: exeo, perfect, second plural"
        )
    },
    "Sion:Sion": {
        "collatinus": (
            "enumerates the indeclinable name in three cases only (nominative, vocative, "
            "accusative); the Psalter's own constructions put it in the rest — ex Sion an "
            "ablative, pópulus Sion a genitive. An indeclinable serves every case, and a "
            "closed list of three is the dictionary's economy, not the word's limit"
        )
    },
    "manifeste:maniféste": {
        "whitakers": (
            "carries only the adjective manifestus, whose vocative shares this surface; "
            "between subject and verb (Deus maniféste véniet) the word is the adverb in "
            "-e, which Collatinus heads and confirms"
        )
    },
    "idem:idípsum": {
        "whitakers": (
            "offers only its adverb idipsum ('at once', the Ps 4:9 idiom); in det vobis "
            "idípsum sápere (Rom 15:5) the fused id+ipsum is the object of sápere — 'to "
            "mind the same thing' — the pronoun, as the whole exegetical tradition of ut "
            "idem sapiátis reads it. Collatinus dictionaries the fusion itself (aliased "
            "above)"
        )
    },
    "alteruter:altérutrum": {
        "whitakers": (
            "files the compound under adjective and adverb; the corpus files the "
            "uter-compounds as pronouns, as it files uter and alter themselves, and in "
            "altérutrum (Rom 15:5) is the pronoun after in. Collatinus confirms the "
            "accusative neuter under the same head"
        )
    },
    "credo:credéndo": {
        "whitakers": (
            "models the gerund as its gerundive and returns future passive readings; in "
            "credéndo (Rom 15:13) is the ablative gerund — believing, not to-be-believed "
            "— the reading SCHEMA.md's own gerund note reserves a ruling for. Collatinus "
            "confirms the ablative under credo"
        )
    },
    "Annas:Anna": {
        "whitakers": (
            "knows the surface only as the imperative of annáre, to swim toward — a "
            "caseless homograph, not the high priest (Lc 3:2). The name declines Annas, "
            "Annæ like the Greek masculines beside it in the verse, and the ablative "
            "stands in the same absolute as Cáipha two words on"
        )
    },
}

# Proper names whose normalized spelling is identical to an ordinary Latin
# dictionary word. The analyzers are case-blind, so a formally matching parse
# of the common noun or adjective cannot confirm the identity of the saint's
# name. The named analyzer abstains from any opinion based on that homograph;
# the same lowercase common word remains fully machine-checkable.
CASEFOLD_HOMOGRAPH_RULINGS: dict[str, dict[str, str]] = {
    "Felicitas:Felicitáte": {
        "whitakers": (
            "carries the common noun felicitas (happiness), not the martyr Felicitas; its "
            "case-folded noun parse cannot establish the proper name"
        ),
        "collatinus": (
            "likewise carries the common noun felicitas rather than the martyr's name; the "
            "matching inflection does not establish lexical identity"
        ),
    },
    # Moved here from FEATURE_RULINGS on 2026-08-19: their old reasons credited
    # Collatinus with "confirming the name" on the strength of the very
    # common-word homographs this table exists to refuse — its Lini candidates
    # are the flax words, its Clemens the adjective. The standard is one
    # standard: a case-folded common word establishes no saint's name, from
    # either analyzer, and the parses rest on the edition (the genitives are
    # secure from the chain of genitives each stands in).
    "Linus:Lini": {
        "whitakers": (
            "carries no pope Linus — only linum (flax) and lino — and reads the case-folded "
            "name as one of them; that match cannot establish the proper name"
        ),
        "collatinus": (
            "likewise heads only lino, linum and their kin at this surface; a flax-word "
            "parse cannot establish the pope's name"
        ),
    },
    "Clemens:Cleméntis": {
        "whitakers": (
            "carries only the adjective clemens, not the pope's name; the adjective's "
            "genitive cannot establish it"
        ),
        "collatinus": (
            "likewise offers the adjective clemens (and clementia); the same formal match "
            "the rule above refuses from Whitaker's cannot count as the name from here"
        ),
    },
    "Perpetua:Perpétua": {
        "whitakers": (
            "carries no martyr Perpetua and reads the case-folded name as the adjective "
            "perpetuus; that formal match cannot establish the proper name"
        ),
        "collatinus": (
            "likewise heads only perpetuus/perpetuum, not the martyr Perpetua; its "
            "case-folded adjective parse cannot establish lexical identity"
        ),
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
        for spelling in link_spellings(word["lemma"])
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
    accepted = {collatinus.fold_lemma(spelling) for spelling in link_spellings(word["lemma"])}
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

    key = f"{word['lemma']}:{word['form']}"

    # A case-blind dictionary match to an ordinary word does not establish a
    # capitalized proper name. Set that named analyzer's opinion aside whether
    # it called the common-word parse matching or contradictory; this never
    # affects the lowercase lexeme.
    identity_rulings = CASEFOLD_HOMOGRAPH_RULINGS.get(key, {})
    ruled = [
        f"{name} set aside: {reason}"
        for name, reason in identity_rulings.items()
        if votes.get(name, ("", ""))[0] in {"CONFIRMS", "FORM_MATCH", "CONTRADICTS"}
    ]
    for name in identity_rulings:
        if votes.get(name, ("", ""))[0] in {"CONFIRMS", "FORM_MATCH", "CONTRADICTS"}:
            votes[name] = ("ABSTAINS", "")

    # An adjudicated contradiction abstains instead of counting against us,
    # and the token is reported as ruled rather than as plain agreement.
    rulings = FEATURE_RULINGS.get(key, {})
    ruled.extend(
        f"{name} set aside: {reason}"
        for name, reason in rulings.items()
        if votes.get(name, ("", ""))[0] == "CONTRADICTS"
    )
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
