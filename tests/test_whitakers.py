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
