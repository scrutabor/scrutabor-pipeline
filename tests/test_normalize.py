from scrutabor_pipeline.normalize import analyzer_query


def test_strips_accents_and_lowercases():
    assert analyzer_query("Confíteor") == "confiteor"
    assert analyzer_query("Ídeo") == "ideo"


def test_folds_ligatures():
    assert analyzer_query("sǽcula") == "saecula"
    assert analyzer_query("cælis") == "caelis"
    assert analyzer_query("beátæ") == "beatae"


def test_j_becomes_i():
    assert analyzer_query("Joánni") == "ioanni"
    assert analyzer_query("Jesus") == "iesus"


def test_diaeresis_folds_to_plain_vowel():
    assert analyzer_query("Míchaël") == "michael"


def test_liturgical_spellings_map_to_dictionary_spellings():
    assert analyzer_query("quotidiánum") == "cotidianum"
    assert analyzer_query("tentatiónem") == "temptationem"
    # the lemma strings map too
    assert analyzer_query("quotidianus") == "cotidianus"
    assert analyzer_query("tentatio") == "temptatio"
