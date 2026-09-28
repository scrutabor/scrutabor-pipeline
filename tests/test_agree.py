from itertools import product

import pytest

from scrutabor_pipeline import agree, whitakers
from scrutabor_pipeline.agree import compare
from scrutabor_pipeline.feature_scopes import FEATURE_SCOPES, FEATURES, feature_ruling_applies


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


def test_lowercase_martyrum_uses_the_reviewed_number_ruling():
    v = compare(
        "t",
        word("mártyrum", "martyr", pos="noun", case="gen", number="pl", gender="m", decl=3),
    )
    assert v.verdict == "AGREE_RULED"
    assert v.sources == "collatinus"


def test_nostri_as_personal_pronoun_is_not_misread_as_possessive():
    v = compare("t", word("nostri", "nos", pos="pron", case="gen", number="pl"))
    assert v.verdict == "AGREE_RULED"
    assert v.sources == "whitakers"


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


def test_discriminated_homonyms_link_without_losing_their_identity():
    for lemma, spelling in {
        "labor_labi": "labor",
        "mundus_purus": "mundus",
        "inimicus_hostilis": "inimicus",
        "adversus_prep": "adversus",
        "sero_adverb": "sero",
        "infernus_inferior": "infernus",
        "occido_cado": "occido",
        "excido_cado": "excido",
        "furor_nomen": "furor",
    }.items():
        assert agree.link_spellings(lemma) == (spelling,)
    assert agree.link_spellings("unregistered_homonym") == ()


def test_outside_adverb_has_its_own_dictionary_identity():
    v = compare("t", word("foris", "foris_adverbium", pos="adv"))
    assert v.verdict == "AGREE"
    assert v.sources == "whitakers+collatinus"
    wrong = compare("t", word("foris", "foris_adverbium", pos="noun", case="acc", number="sg"))
    assert wrong.verdict == "DIVERGE"


def test_dedication_gerundive_can_link_its_discriminated_lemma():
    token = word(
        "dicánda",
        "dico_dedicare",
        pos="verb",
        mood="part",
        tense="fut",
        voice="pass",
        case="nom",
        number="sg",
        gender="f",
        conj=1,
    )
    assert compare("t", token).sources == "whitakers+collatinus"
    token["morph"]["case"] = "gen"
    assert compare("t", token).verdict == "DIVERGE"


def test_fused_tecum_is_linked_by_alias():
    v = compare("t", word("tecum", "tu", pos="pron", case="abl", number="sg"))
    assert v.verdict == "AGREE"


# --- adjudicated contradictions (FEATURE_RULINGS) -------------------------


def test_accented_indeclinable_israel_dative_reports_case_limitation(monkeypatch):
    token = word("Ísrael", "Israel", pos="noun", case="dat", number="sg", gender="m")
    result = compare("t", token)
    assert result.verdict == "AGREE_RULED"
    assert result.sources == "collatinus"
    assert "case open" in result.detail
    monkeypatch.delitem(agree.FEATURE_RULINGS, "Israel:Ísrael")
    assert compare("t", token).verdict == "DIVERGE"


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


def test_actus_contritionis_rulings_preserve_independent_confirmation():
    examples = (
        word(
            "peccándo",
            "pecco",
            pos="verb",
            case="abl",
            number="sg",
            gender="n",
            tense="pres",
            mood="ger",
            voice="act",
            conj=1,
        ),
        word(
            "peccandíque",
            "pecco",
            pos="verb",
            case="gen",
            number="sg",
            gender="n",
            tense="pres",
            mood="ger",
            voice="act",
            conj=1,
        ),
        word(
            "summum",
            "summus",
            pos="adj",
            case="acc",
            number="sg",
            gender="n",
            degree="sup",
        ),
        word(
            "próximas",
            "proximus",
            pos="adj",
            case="acc",
            number="pl",
            gender="f",
        ),
    )
    for example in examples:
        verdict = compare("t", example)
        assert verdict.verdict == "AGREE_RULED"
        assert verdict.sources == "collatinus"
        assert "whitakers set aside" in verdict.detail


def test_a_ruling_does_not_cover_a_different_word():
    """Rulings are keyed to lemma AND form: they cannot leak."""
    v = compare("t", word("vestris", "vos", pos="pron", case="gen", number="pl"))
    assert v.verdict != "AGREE_RULED"


@pytest.mark.parametrize(
    ("form", "lemma", "morph"),
    [
        ("abýssus", "abyssus", dict(pos="noun", case="voc", number="sg", gender="f")),
        (
            "prióri",
            "prior",
            dict(pos="adj", case="abl", number="sg", gender="n", degree="comp"),
        ),
        ("Ísrael", "Israel", dict(pos="noun", case="dat", number="sg", gender="m")),
    ],
)
@pytest.mark.parametrize(("feature", "value"), [("number", "pl"), ("pos", "verb")])
def test_per_form_ruling_does_not_hide_unrelated_feature_errors(form, lemma, morph, feature, value):
    wrong = {**morph, feature: value}
    assert compare("t", word(form, lemma, **wrong)).verdict == "DIVERGE"


@pytest.mark.parametrize("case", ["gen", "dat", "acc", "abl"])
def test_vocative_ruling_does_not_license_other_cases(case):
    token = word("abýssus", "abyssus", pos="noun", case=case, number="sg", gender="f")
    assert compare("t", token).verdict == "DIVERGE"


def test_indeclinable_case_ruling_does_not_hide_wrong_gender():
    token = word("Ísrael", "Israel", pos="noun", case="dat", number="sg", gender="f")
    assert compare("t", token).verdict == "DIVERGE"


def test_every_per_form_ruling_has_an_explicit_grammatical_scope():
    assert set(FEATURE_SCOPES) == set(agree.FEATURE_RULINGS)
    assert set(FEATURES) == {"pos", *agree.COMPARED}
    for variants in FEATURE_SCOPES.values():
        assert variants
        for candidate in variants:
            assert "pos" in candidate
            assert set(candidate) <= set(FEATURES)
            assert all(candidate.values())


@pytest.mark.parametrize("key", sorted(FEATURE_SCOPES))
def test_per_form_ruling_scope_is_enforced_for_each_compared_feature(key, monkeypatch):
    # Isolate dispatch from dictionary coverage: each named analyzer always
    # contradicts, the others are absent. Check every declared alternative,
    # then mutate one feature at a time outside ALL alternatives of this rule.
    for name in ("whitakers", "collatinus"):
        vote = "CONTRADICTS" if name in agree.FEATURE_RULINGS[key] else "ABSENT"
        monkeypatch.setattr(agree, f"_{name}_vote", lambda *args, vote=vote: (vote, "control"))
    lemma, form = key.split(":")
    values = {
        "pos": (None, "noun", "adj", "verb", "pron", "adv", "prep"),
        "case": (None, "nom", "gen", "dat", "acc", "abl", "voc", "loc"),
        "number": (None, "sg", "pl"),
        "gender": (None, "m", "f", "n"),
        "person": (None, 1, 2, 3),
        "tense": (None, "pres", "perf", "fut", "futperf"),
        "mood": (None, "ind", "subj", "imp", "inf", "part", "ger"),
        "voice": (None, "act", "pass", "dep"),
        "degree": (None, "pos", "comp", "sup"),
    }
    mutations = 0
    for candidate in FEATURE_SCOPES[key]:
        for combination in product(*candidate.values()):
            morph = dict(zip(candidate, combination, strict=True))
            assert compare("control", word(form, lemma, **morph)).verdict == "EDITORIAL_ONLY"
            for feature in FEATURES:
                for value in values[feature]:
                    changed = {**morph, feature: value}
                    # Derive the expected domain directly from the declarations,
                    # not by asking the function under test to classify it.
                    allowed = any(
                        all(changed.get(f) in alternative.get(f, (None,)) for f in FEATURES)
                        for alternative in FEATURE_SCOPES[key]
                    )
                    if not allowed:
                        mutations += 1
                        assert not feature_ruling_applies(key, changed)
                        assert compare("control", word(form, lemma, **changed)).verdict == "DIVERGE"
    assert mutations > 0


def test_a_new_unscoped_ruling_cannot_discard_a_contradiction(monkeypatch):
    monkeypatch.setitem(agree.FEATURE_RULINGS, "mater:Mater", {"whitakers": "unscoped"})
    token = word("Mater", "mater", pos="noun", case="acc", number="sg", gender="f")
    assert compare("t", token).verdict == "DIVERGE"


def test_summis_adjective_retains_collatinus_confirmation():
    verdict = compare(
        "t",
        word("summis", "summus", pos="adj", case="dat", number="pl", gender="n", degree="sup"),
    )
    assert verdict.verdict == "AGREE_RULED"
    assert verdict.sources == "collatinus"
    assert "whitakers set aside" in verdict.detail


def test_venerando_gerund_retains_independent_confirmation():
    verdict = compare(
        "t",
        word(
            "venerándo",
            "veneror",
            pos="verb",
            case="abl",
            number="sg",
            gender="n",
            tense="pres",
            voice="act",
            mood="ger",
            conj=1,
        ),
    )
    assert verdict.verdict == "AGREE_RULED"
    assert verdict.sources == "collatinus"
    assert "whitakers set aside" in verdict.detail


def test_venerando_ruling_does_not_license_an_accusative():
    verdict = compare(
        "t",
        word(
            "venerándo",
            "veneror",
            pos="verb",
            case="acc",
            number="sg",
            gender="n",
            tense="pres",
            voice="act",
            mood="ger",
            conj=1,
        ),
    )
    assert verdict.verdict == "DIVERGE"


def test_summis_ruling_does_not_license_an_impossible_accusative():
    verdict = compare(
        "t",
        word("summis", "summus", pos="adj", case="acc", number="pl", gender="n", degree="sup"),
    )
    assert verdict.verdict == "DIVERGE"


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


def test_an_unaliased_discriminated_lemma_gets_a_verdict_not_a_crash():
    """A homograph discriminator without its LEMMA_ALIASES entry is the shape
    that killed the whole report from 2026-08-18 (liber_volumen): the raw
    underscore key reached Whitaker's as a word and the comparison raised.
    One bad token must cost that token its lemma link, never the report.
    """
    from scrutabor_pipeline.agree import compare, link_spellings

    assert link_spellings("panis_cibus") == ()
    word = {
        "id": "w001",
        "form": "panem",
        "lemma": "panis_cibus",
        "morph": {"pos": "noun", "case": "acc", "number": "sg", "gender": "m"},
    }
    verdict = compare("test.text", word)
    assert verdict.verdict in {"AGREE_FORM_ONLY", "EDITORIAL_ONLY", "FORM_ABSENT", "DIVERGE"}


def test_gerund_sets_whitakers_aside_for_its_missing_category():
    # Whitaker's has no gerund and prints moriéndi as the gerundive; it is set
    # aside with the reason, never counted as confirming the gerund.
    gerund = word(
        "moriéndi",
        "morior",
        pos="verb",
        mood="ger",
        tense="pres",
        voice="act",
        case="gen",
        number="sg",
        gender="n",
        conj=3,
    )
    verdict = compare("t", gerund)
    assert verdict.verdict in {"AGREE_RULED", "EDITORIAL_ONLY"}
    assert "whitakers" not in verdict.sources.split("+")
    assert "has no gerund" in verdict.detail
    gerund["morph"]["case"] = "dat"
    assert compare("t", gerund).verdict == "DIVERGE"


def test_ii_genitive_sets_whitakers_aside_for_its_locative_only_table():
    genitive = word(
        "sacrifícii", "sacrificium", pos="noun", case="gen", number="sg", gender="n", decl=2
    )
    verdict = compare("t", genitive)
    assert verdict.verdict in {"AGREE_RULED", "EDITORIAL_ONLY"}
    assert "whitakers" not in verdict.sources.split("+")
    genitive["morph"]["case"] = "dat"
    assert compare("t", genitive).verdict == "DIVERGE"


@pytest.mark.parametrize(
    ("feature", "value"),
    [("number", "pl"), ("gender", "f"), ("tense", "perf"), ("voice", "pass"), ("person", 3)],
)
def test_gerund_category_gap_does_not_hide_other_wrong_features(feature, value):
    gerund = word(
        "moriéndi",
        "morior",
        pos="verb",
        mood="ger",
        tense="pres",
        voice="act",
        case="gen",
        number="sg",
        gender="n",
        conj=3,
    )
    gerund["morph"][feature] = value
    verdict = compare("t", gerund)
    assert verdict.verdict == "DIVERGE"
    assert "has no gerund" not in verdict.detail


@pytest.mark.parametrize(("pos", "decl"), [("adj", 2), ("noun", 3)])
def test_ii_gap_is_limited_to_second_declension_nouns(monkeypatch, pos, decl):
    candidate = whitakers.Candidate(1, pos, (("case", "loc"), ("number", "sg"), ("gender", "n")))
    monkeypatch.setattr(whitakers, "candidates", lambda _: [candidate])
    monkeypatch.setattr(whitakers, "lemma_candidates", lambda _: [candidate])
    ours = {"case": "gen", "number": "sg", "gender": "n", "decl": decl}
    vote, _ = agree._whitakers_vote(word("sacrifícii", "sacrificium"), pos, ours)
    assert vote == "CONTRADICTS"


def test_category_gap_cannot_be_inferred_from_an_unrelated_lemma(monkeypatch):
    form_candidate = whitakers.Candidate(
        1,
        "verb",
        (("tense", "fut"), ("voice", "pass"), ("case", "gen"), ("number", "sg"), ("gender", "n")),
    )
    lemma_candidate = whitakers.Candidate(2, "verb")
    monkeypatch.setattr(whitakers, "candidates", lambda _: [form_candidate])
    monkeypatch.setattr(whitakers, "lemma_candidates", lambda _: [lemma_candidate])
    ours = {
        "mood": "ger",
        "tense": "pres",
        "voice": "act",
        "case": "gen",
        "number": "sg",
        "gender": "n",
    }
    vote, _ = agree._whitakers_vote(word("moriéndi", "morior"), "verb", ours)
    assert vote == "CONTRADICTS"


def test_ii_genitive_with_an_actual_genitive_reading_still_confirms():
    genitive = word(
        "Evangélii", "evangelium", pos="noun", case="gen", number="sg", gender="n", decl=2
    )
    verdict = compare("t", genitive)
    assert "whitakers" in verdict.sources.split("+")
