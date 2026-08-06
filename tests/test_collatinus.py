from scrutabor_pipeline.collatinus import candidates, fold_lemma, parse_morph


def test_parse_morph_maps_french_vocabulary():
    assert parse_morph("2ème singulier subjonctif présent actif") == {
        "person": 2,
        "number": "sg",
        "mood": "subj",
        "tense": "pres",
        "voice": "act",
    }
    assert parse_morph("vocatif singulier") == {"case": "voc", "number": "sg"}
    assert parse_morph("ablatif féminin pluriel") == {
        "case": "abl",
        "gender": "f",
        "number": "pl",
    }


def test_parse_morph_matches_two_word_tenses_first():
    assert parse_morph("3ème singulier indicatif plus-que-parfait actif")["tense"] == "plup"
    assert parse_morph("3ème singulier indicatif futur antérieur actif")["tense"] == "futperf"
    assert parse_morph("3ème singulier indicatif futur actif")["tense"] == "fut"


def test_parse_morph_indeclinable_is_open():
    assert parse_morph("-") == {}


def test_fold_lemma_bridges_orthographies():
    # Collatinus lemmatizes in classical u-style and may number homonyms
    assert fold_lemma("aveo") == fold_lemma("aueo")
    assert fold_lemma("Ioannes") == fold_lemma("Joannes")
    assert fold_lemma("dico2") == fold_lemma("dico")
    assert fold_lemma("quotidianus") == fold_lemma("cotidianus")


def test_collatinus_knows_the_hebrew_proper_names():
    michael = candidates("Michaéli")
    assert any(c.lemma == "michael" and c.feature_dict().get("case") == "dat" for c in michael)
    iesus = candidates("Jesus")
    assert any(c.lemma == "iesus" for c in iesus)


def test_collatinus_reads_liturgical_orthography_via_normalization():
    cands = candidates("sǽcula")
    assert any(c.lemma == "saeculum" and c.feature_dict().get("case") == "acc" for c in cands)


def test_parse_morph_maps_participle():
    from scrutabor_pipeline.collatinus import parse_morph

    features = parse_morph("participe parfait passif accusatif masculin singulier")
    assert features == {
        "mood": "part",
        "tense": "perf",
        "voice": "pass",
        "case": "acc",
        "gender": "m",
        "number": "sg",
    }
