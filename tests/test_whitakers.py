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
        f.get("voice") == "pass" and f.get("person") == 1 and f.get("mood") == "ind"
        for f in verb
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
