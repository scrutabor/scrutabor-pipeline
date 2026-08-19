from scrutabor_pipeline import agree
from scrutabor_pipeline.agree import compare


def word(form, lemma, **morph):
    return {"id": "w001", "form": form, "lemma": lemma, "morph": morph}


def test_correct_parse_agrees_by_both_analyzers():
    v = compare(
        "t", word("Mater", "mater", pos="noun", case="voc", number="sg", gender="f", decl=3)
    )
    assert v.verdict == "AGREE"
    assert v.sources == "whitakers+collatinus"


def test_wrong_parse_diverges():
    # mater cannot be accusative — the guard must catch a wrong editorial parse
    v = compare(
        "t", word("Mater", "mater", pos="noun", case="acc", number="sg", gender="f", decl=3)
    )
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


# --- adjudicated contradictions (FEATURE_RULINGS) -------------------------


def test_ruling_sets_one_analyzer_aside_and_says_so():
    """A recorded ruling turns a contradiction into an abstention — and the
    token is reported as ruled, never as plain agreement."""
    v = compare("t", word("vestri", "vos", pos="pron", case="gen", number="pl"))
    assert v.verdict == "AGREE_RULED"
    assert "whitakers" in v.sources
    assert "collatinus set aside" in v.detail


def test_ruling_never_invents_a_confirmation():
    """With the only analyzer that knows the form set aside, nothing
    machine-checkable remains and the verdict says exactly that."""
    v = compare(
        "t",
        word(
            "quǽsumus",
            "quaeso",
            pos="verb",
            person=1,
            number="pl",
            tense="pres",
            mood="ind",
            voice="act",
            conj=3,
        ),
    )
    assert v.verdict == "EDITORIAL_ONLY"
    assert "no analyzer confirms" in v.detail


def test_pressura_ruling_preserves_independent_confirmation():
    v = compare(
        "t",
        word(
            "pressúra",
            "pressura",
            pos="noun",
            case="nom",
            number="sg",
            gender="f",
            decl=1,
        ),
    )
    assert v.verdict == "AGREE_RULED"
    assert v.sources == "collatinus"
    assert "whitakers set aside" in v.detail


def test_a_ruling_does_not_cover_a_different_word():
    """Rulings are keyed to lemma AND form: they cannot leak."""
    v = compare("t", word("vestris", "vos", pos="pron", case="gen", number="pl"))
    assert v.verdict != "AGREE_RULED"


def test_casefold_homograph_does_not_confirm_saint_felicitas():
    v = compare(
        "t",
        word(
            "Felicitáte",
            "Felicitas",
            pos="noun",
            case="abl",
            number="sg",
            gender="f",
            decl=3,
        ),
    )
    assert v.verdict == "EDITORIAL_ONLY"
    assert "common noun felicitas" in v.detail


def test_casefold_homograph_does_not_confirm_saint_perpetua():
    v = compare(
        "t",
        word(
            "Perpétua",
            "Perpetua",
            pos="noun",
            case="abl",
            number="sg",
            gender="f",
            decl=1,
        ),
    )
    assert v.verdict == "EDITORIAL_ONLY"
    assert "martyr Perpetua" in v.detail


def test_casefold_homograph_ruling_does_not_hide_common_noun():
    v = compare(
        "t",
        word(
            "felicitáte",
            "felicitas",
            pos="noun",
            case="abl",
            number="sg",
            gender="f",
            decl=3,
        ),
    )
    assert v.verdict == "AGREE"


def test_every_ruling_carries_a_reason():
    for rulings in (agree.FEATURE_RULINGS, agree.CASEFOLD_HOMOGRAPH_RULINGS):
        for key, analyzers in rulings.items():
            assert analyzers, f"{key}: empty ruling"
            for name, reason in analyzers.items():
                assert name in ("whitakers", "collatinus"), f"{key}: unknown analyzer {name}"
                assert len(reason) > 40, f"{key}/{name}: a ruling must argue itself"


def test_declared_analyzers_reads_the_corpus_as_it_is_stored():
    """The shape schema 0.14.0 actually writes: one document per text with
    every editorial claim under `editorial`.

    This test built the PRE-0.14.0 shape until 2026-08-19 and passed for
    months against a corpus that had stopped existing — so the report it
    guards silently found that no word claimed any analyzer, and no gate
    said a word. A fixture that describes a shape nobody writes is not a
    test, it is a second opinion about the past.
    """
    from scrutabor_pipeline.agreement import declared_analyzers

    doc = {
        "editorial": {
            "analysis_defaults": {"sources": ["editorial"]},
            "analysis_defaults_words": {"sources": ["editorial", "whitakers", "collatinus"]},
            "words": {"w001": {"analysis": {"sources": ["editorial", "collatinus"]}}},
        }
    }
    assert declared_analyzers(doc, {"id": "w002", "form": "x"}) == {"whitakers", "collatinus"}
    assert declared_analyzers(doc, {"id": "w001", "form": "x"}) == {"collatinus"}
    bare = {"editorial": {"analysis_defaults": {"sources": ["editorial"]}}}
    assert declared_analyzers(bare, {"id": "w001", "form": "x"}) == set()


def test_declared_analyzers_still_reads_the_older_shape():
    """The pipeline is not versioned with the corpus and may be pointed at an
    older checkout, so the pre-0.14.0 cascade is still honoured."""
    from scrutabor_pipeline.agreement import declared_analyzers

    doc = {
        "analysis_defaults": {"sources": ["editorial"]},
        "analysis_defaults_words": {"sources": ["editorial", "whitakers", "collatinus"]},
    }
    assert declared_analyzers(doc, {"form": "x"}) == {"whitakers", "collatinus"}
    narrower = {"form": "x", "analysis": {"sources": ["editorial", "collatinus"]}}
    assert declared_analyzers(doc, narrower) == {"collatinus"}
    witness_only = {"form": "x", "analysis": {"sources": ["editorial", "do"]}}
    assert declared_analyzers(doc, witness_only) == set()
    assert (
        declared_analyzers({"analysis_defaults": {"sources": ["editorial"]}}, {"form": "x"})
        == set()
    )
