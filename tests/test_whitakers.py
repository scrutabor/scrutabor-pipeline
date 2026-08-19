from scrutabor_pipeline import whitakers
from scrutabor_pipeline.whitakers import candidates, lemma_candidates


def test_ambiguous_noun_offers_both_cases():
    cands = candidates("Mater")
    features = [c.feature_dict() for c in cands if c.pos == "noun"]
    cases = {f.get("case") for f in features}
    assert "voc" in cases and "nom" in cases


def test_deponent_form_comes_back_passive():
    cands = candidates("Confíteor")
    verb = [c.feature_dict() for c in cands if c.pos == "verb"]
    assert any(
        f.get("voice") == "pass" and f.get("person") == 1 and f.get("mood") == "ind" for f in verb
    )


def test_sicut_offers_both_classifications():
    poses = {c.pos for c in candidates("sicut")}
    assert {"conj", "adv"} <= poses


def test_heteroclite_plural_offers_masculine_heaven():
    cands = candidates("cælis")
    assert any(
        c.pos == "noun"
        and c.feature_dict().get("gender") == "m"
        and c.feature_dict().get("case") == "abl"
        for c in cands
    )


def test_unknown_proper_name_yields_nothing():
    assert candidates("Michaéli") == []


def test_lemma_links_to_its_own_entry():
    ids = {c.lexeme_id for c in lemma_candidates("confiteor") if c.pos == "verb"}
    assert ids
    form_ids = {c.lexeme_id for c in candidates("Confíteor") if c.pos == "verb"}
    assert ids & form_ids


def test_ecclesiastical_vocabulary_is_admitted():
    # the port's default frequency floor drops these; Parser(frequency='E') admits them
    assert any(
        c.pos == "noun" and c.feature_dict().get("case") == "abl"
        for c in candidates("peccatóribus")
    )
    assert any(
        c.pos == "verb" and c.feature_dict().get("mood") == "subj"
        for c in candidates("Sanctificétur")
    )
    assert any(c.pos == "adj" for c in candidates("omnipoténti"))
    assert any(c.pos == "noun" for c in candidates("Archángelo"))
    assert any(c.pos == "noun" for c in candidates("tentatiónem"))


def test_participle_maps_to_verb_with_open_mood():
    # natum: perfect passive participle of nascor/natus (and of gigno's
    # natus) — Whitaker's VPAR must come back as a verb candidate whose
    # mood is open (matching the corpus's mood "part") with tense and
    # voice stated.
    from scrutabor_pipeline.whitakers import candidates

    parts = [
        c
        for c in candidates("natum")
        if c.pos == "verb"
        and dict(c.features).get("tense") == "perf"
        and dict(c.features).get("voice") == "pass"
    ]
    assert parts, "no perfect passive participle candidate for natum"
    assert all(dict(c.features).get("mood") is None for c in parts)


def test_ordinal_numeral_comes_back_as_adjective():
    # tertia: Whitaker's heads ordinals as NUM; the corpus tags them adj.
    from scrutabor_pipeline.whitakers import candidates

    readings = [
        c
        for c in candidates("tertia")
        if c.pos == "adj"
        and dict(c.features).get("case") == "abl"
        and dict(c.features).get("gender") == "f"
    ]
    assert readings, "no ablative feminine adjective candidate for tertia"


def test_knows_the_words_whose_consonant_is_spelled_i():
    # This analyzer was silent on every one of these while the query folded
    # j to i: its dictionary spells them with j. The corpus prints i
    # (ORTHOGRAPHY.md), so the wrapper has to translate.
    for form in ("Iesu", "iube", "maiestátis", "Adiutórium", "Ioánnem", "iustum", "Iúdica"):
        assert candidates(form), f"{form}: no reading"


def test_knows_the_pronoun_forms_its_tables_spell_with_i():
    # ...and the same analyzer generates eius in i, so both spellings are
    # asked and the union is taken.
    for form in ("eius", "eiúsdem", "cuius", "huius"):
        assert candidates(form), f"{form}: no reading"


def test_knows_the_greek_loans_the_liturgical_books_spell_with_y():
    # This analyzer returns nothing for either liturgical spelling, so both
    # words rested on Collatinus alone until the spelling table carried them
    # to the heads it does carry: lacrima, Hierosolyma.
    for form in ("lacrymárum", "Ierosólymis"):
        assert candidates(form), f"{form}: no reading"


# --- the tables may hold no dead key --------------------------------------


def test_every_mapping_key_is_a_name_the_analyzer_uses():
    """A key naming nothing is a branch that never runs, and the feature it
    was written for is dropped instead of translated — silently, because a
    missing name and an unmapped value both come out as None. DEGREE spelled
    the superlative SUP, which this port's enum calls SUPER, so every
    superlative reached the corpus with its degree open until 2026-08-19.
    The enums are the only authority on the names.
    """
    from whitakers_words.enums import Case, Degree, Gender, Mood, Number, Tense, Voice, WordType

    tables = {
        "POS": (whitakers.POS, WordType),
        "CASE": (whitakers.CASE, Case),
        "NUMBER": (whitakers.NUMBER, Number),
        "GENDER": (whitakers.GENDER, Gender),
        "TENSE": (whitakers.TENSE, Tense),
        "MOOD": (whitakers.MOOD, Mood),
        "VOICE": (whitakers.VOICE, Voice),
        "DEGREE": (whitakers.DEGREE, Degree),
    }
    for name, (table, enum) in tables.items():
        unknown = sorted(set(table) - {member.name for member in enum})
        assert not unknown, f"{name}: {unknown} name no member of {enum.__name__}"


def test_every_part_of_speech_key_is_one_a_lexeme_can_carry():
    """Membership of WordType is not enough for POS: the adapter reads the
    word type of the LEXEME, and the port's dictionary heads no lexeme as
    VPAR — that word type belongs to inflections alone. A key for it would
    match nothing while looking like the thing that makes participles work.
    """
    from whitakers_words.generated.stems import stems
    from whitakers_words.generated.uniques import uniques

    heads = {entry["pos"] for entries in stems.values() for entry in entries}
    heads |= {entry["pos"] for entries in uniques.values() for entry in entries}
    assert heads, "no dictionary heads read — the check would pass on nothing"
    unreachable = sorted(set(whitakers.POS) - heads)
    assert not unreachable, f"POS: {unreachable} head no entry in the analyzer's dictionary"


# --- one certain reading per mapped value ---------------------------------

# (form, feature, mapped value, what makes the reading certain). Every value
# the tables can produce for a feature is claimed by some form here, so a
# corrupted entry fails in this file instead of travelling into a verdict:
# changing any one of DAT, LOC, N, IMPF, FUT, PLUP, FUTP, IMP, INF, COMP or
# SUPER left the whole suite green until 2026-08-19.
FEATURE_ORACLES = [
    ("Dómino", "case", "dat", "dative singular of dominus"),
    ("domi", "case", "loc", "the locative of domus — a case the corpus has none of"),
    ("sǽcula", "gender", "n", "neuter plural of saeculum"),
    ("erat", "tense", "impf", "imperfect of sum"),
    ("véniet", "tense", "fut", "future of venio"),
    ("fúerant", "tense", "plup", "pluperfect of sum"),
    ("fúerit", "tense", "futperf", "future perfect of sum"),
    ("veni", "mood", "imp", "singular imperative of venio"),
    ("esse", "mood", "inf", "present infinitive of sum"),
    ("purióres", "degree", "comp", "comparative of purus"),
    ("Altíssimus", "degree", "sup", "superlative of altus"),
]


def test_each_mapped_feature_value_is_reached_by_a_form_that_carries_it():
    for form, feature, value, why in FEATURE_ORACLES:
        offered = {c.feature_dict().get(feature) for c in candidates(form)}
        assert value in offered, (
            f"{form} ({why}): no candidate with {feature}={value}, got {offered}"
        )


def test_the_acclamation_comes_back_an_interjection():
    # allelúia is intj in the corpus and INTERJ here. amen is not the example
    # to use: this analyzer heads it as an adverb, which is why the corpus
    # records a part-of-speech ruling for the indeclinable Hebrew loans.
    assert "intj" in {c.pos for c in candidates("Allelúia")}


def test_the_participle_arrives_under_the_verb_head():
    # locútus: perfect participle of the deponent loquor. Its inflection is
    # the analyzer's VPAR, which states no mood — but its LEXEME is a verb,
    # which is the only key the table needs.
    parts = [c for c in candidates("locútus") if c.pos == "verb"]
    assert parts, "no verb candidate for locútus"
    assert all("mood" not in c.feature_dict() for c in parts)
    assert any(c.feature_dict().get("voice") == "pass" for c in parts)
