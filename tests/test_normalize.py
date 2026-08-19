from scrutabor_pipeline.normalize import analyzer_query, whitakers_query


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


def test_greek_loans_lose_the_y_and_regain_the_aspirate():
    assert analyzer_query("lacrymárum") == "lacrimarum"
    assert analyzer_query("Ierosólymis") == "hierosolymis"
    # both sides of the identity link are folded through here
    assert analyzer_query("lacryma") == "lacrima"
    assert analyzer_query("Ierosolyma") == "hierosolyma"
    # the restored aspirate moves the i off the head of the word, so the
    # glide rule leaves it vocalic — which is how the dictionary spells it
    assert whitakers_query("Ierosólymis") == "hierosolymis"


def test_whitakers_query_writes_the_glide_as_j():
    # its dictionary heads the consonant as j; the i-form finds nothing
    assert whitakers_query("Iesu") == "jesu"
    assert whitakers_query("iube") == "jube"
    assert whitakers_query("maiestátis") == "majestatis"
    assert whitakers_query("cuius") == "cujus"
    assert whitakers_query("Ioánnem") == "joannem"


def test_whitakers_query_crosses_a_prefix_seam():
    # ad + iuvo keeps the consonant of its simplex
    assert whitakers_query("Adiutórium") == "adjutorium"
    assert whitakers_query("adiúti") == "adjuti"


def test_whitakers_query_leaves_vocalic_i_alone():
    # the u of qu is a glide, so the i of quia has no vowel before it
    assert whitakers_query("quia") == "quia"
    assert whitakers_query("relíquiæ") == "reliquiae"
    # ordinary vocalic i, wherever it stands
    assert whitakers_query("fílii") == "filii"
    assert whitakers_query("ita") == "ita"
    assert whitakers_query("grátia") == "gratia"
    # the compounds of eo have a real vowel in the same position
    assert whitakers_query("ábiit") == "abiit"
