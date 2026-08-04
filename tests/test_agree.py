from scrutabor_pipeline.agree import compare


def word(form, lemma, **morph):
    return {"id": "w001", "form": form, "lemma": lemma, "morph": morph}


def test_correct_parse_agrees_by_both_analyzers():
    v = compare("t", word("Mater", "mater", pos="noun", case="voc", number="sg", gender="f", decl=3))
    assert v.verdict == "AGREE"
    assert v.sources == "whitakers+collatinus"


def test_wrong_parse_diverges():
    # mater cannot be accusative — the guard must catch a wrong editorial parse
    v = compare("t", word("Mater", "mater", pos="noun", case="acc", number="sg", gender="f", decl=3))
    assert v.verdict == "DIVERGE"


def test_deponent_matches_passive_form():
    v = compare(
        "t",
        word(
            "Confíteor",
            "confiteor",
            pos="verb",
            person=1,
            number="sg",
            tense="pres",
            mood="ind",
            voice="dep",
            conj=2,
        ),
    )
    assert v.verdict == "AGREE"


def test_active_claim_on_deponent_form_diverges():
    v = compare(
        "t",
        word(
            "Confíteor",
            "confiteor",
            pos="verb",
            person=1,
            number="sg",
            tense="pres",
            mood="ind",
            voice="act",
            conj=2,
        ),
    )
    assert v.verdict == "DIVERGE"


def test_proper_name_confirmed_by_collatinus_alone():
    v = compare(
        "t", word("Michaéli", "Michael", pos="noun", case="dat", number="sg", gender="m", decl=3)
    )
    assert v.verdict == "AGREE"
    assert v.sources == "collatinus"


def test_interjection_ruling_still_links_lemma():
    v = compare("t", word("Amen", "amen", pos="intj"))
    assert v.verdict == "AGREE"


def test_subjunctive_agrees():
    v = compare(
        "t",
        word(
            "indúcas",
            "induco",
            pos="verb",
            person=2,
            number="sg",
            tense="pres",
            mood="subj",
            voice="act",
            conj=3,
        ),
    )
    assert v.verdict == "AGREE"


def test_spelling_mapped_lemma_agrees():
    v = compare(
        "t",
        word(
            "quotidiánum",
            "quotidianus",
            pos="adj",
            case="acc",
            number="sg",
            gender="m",
        ),
    )
    assert v.verdict == "AGREE"


def test_lemma_alias_links_a_to_ab():
    v = compare("t", word("a", "ab", pos="prep", governs="abl"))
    assert v.verdict == "AGREE"
    assert "whitakers" in v.sources


def test_fused_tecum_is_linked_by_alias():
    v = compare("t", word("tecum", "tu", pos="pron", case="abl", number="sg"))
    assert v.verdict == "AGREE"
