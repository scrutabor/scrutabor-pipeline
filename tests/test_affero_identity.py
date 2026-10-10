"""Assimilated spelling links one verb, never unrelated features or lemmas."""

from copy import deepcopy

import pytest

from scrutabor_pipeline import agree, collatinus

FORMS = [
    (
        "afferéntur",
        {
            "pos": "verb",
            "mood": "ind",
            "number": "pl",
            "person": 3,
            "tense": "fut",
            "voice": "pass",
            "conj": 3,
        },
    ),
    (
        "affer",
        {
            "pos": "verb",
            "mood": "imp",
            "number": "sg",
            "person": 2,
            "tense": "pres",
            "voice": "act",
            "conj": 3,
        },
    ),
    (
        "áttulit",
        {
            "pos": "verb",
            "mood": "ind",
            "number": "sg",
            "person": 3,
            "tense": "perf",
            "voice": "act",
            "conj": 3,
        },
    ),
    (
        "affértis",
        {
            "pos": "verb",
            "mood": "ind",
            "number": "pl",
            "person": 2,
            "tense": "pres",
            "voice": "act",
            "conj": 3,
        },
    ),
    (
        "afferátis",
        {
            "pos": "verb",
            "mood": "subj",
            "number": "pl",
            "person": 2,
            "tense": "pres",
            "voice": "act",
            "conj": 3,
        },
    ),
    (
        "affert",
        {
            "pos": "verb",
            "mood": "ind",
            "number": "sg",
            "person": 3,
            "tense": "pres",
            "voice": "act",
            "conj": 3,
        },
    ),
    (
        "afferátis",
        {
            "pos": "verb",
            "mood": "subj",
            "number": "pl",
            "person": 2,
            "tense": "pres",
            "voice": "act",
            "conj": 3,
        },
    ),
    (
        "affer",
        {
            "conj": 3,
            "mood": "imp",
            "number": "sg",
            "person": 2,
            "pos": "verb",
            "tense": "pres",
            "voice": "act",
        },
    ),
    (
        "allátam",
        {
            "pos": "verb",
            "case": "acc",
            "number": "sg",
            "gender": "f",
            "tense": "perf",
            "mood": "part",
            "voice": "pass",
            "conj": 3,
        },
    ),
    (
        "áfferunt",
        {
            "pos": "verb",
            "mood": "ind",
            "number": "pl",
            "person": 3,
            "tense": "pres",
            "voice": "act",
            "conj": 3,
        },
    ),
]


def token(form, morph):
    return {"id": "w001", "form": form, "lemma": "affero", "morph": dict(morph)}


def test_only_exact_registered_alias_is_added():
    assert agree.link_spellings("affero") == ("affero", "adfero")
    assert agree.link_spellings("adfero") == ("adfero",)
    assert agree.link_spellings("effero") == ("effero",)
    assert agree.link_spellings("affero_unregistered") == ()


@pytest.mark.parametrize(("form", "morph"), FORMS)
def test_actual_form_confirms_and_alias_removal_exposes_identity_gap(form, morph, monkeypatch):
    word = token(form, morph)
    assert any(
        c.lemma == "adfero" and agree._features_match(morph, c.feature_dict())
        for c in collatinus.candidates(form)
    )
    good = agree.compare("t", word)
    assert good.verdict == "AGREE"
    assert good.sources == "whitakers+collatinus"
    with monkeypatch.context() as control:
        control.delitem(agree.LEMMA_ALIASES, "affero")
        removed = agree.compare("t", word)
        assert removed.sources == "whitakers"
        assert agree._collatinus_vote(word, "verb", morph)[0] == "FORM_MATCH"
    assert agree.compare("t", word) == good


@pytest.mark.parametrize(("form", "morph"), FORMS)
@pytest.mark.parametrize("lemma", ("effero", "affero_unregistered"))
def test_alias_does_not_establish_an_unrelated_lemma(form, morph, lemma):
    word = token(form, morph)
    word["lemma"] = lemma
    assert agree.compare("t", word).sources != "whitakers+collatinus"
    assert agree.compare("t", token(form, morph)).sources == "whitakers+collatinus"


@pytest.mark.parametrize(("form", "morph"), FORMS)
@pytest.mark.parametrize("feature", ("number", "tense", "voice"))
def test_alias_cannot_supply_confirmation_for_incompatible_features(form, morph, feature):
    word = token(form, morph)
    bad = deepcopy(word)
    alternatives = {
        "number": "sg" if morph["number"] == "pl" else "pl",
        "tense": "fut" if morph["tense"] == "pres" else "pres",
        "voice": "pass" if morph["voice"] == "act" else "act",
    }
    bad["morph"][feature] = alternatives[feature]
    result = agree.compare("t", bad)
    assert not result.sources
    assert result.verdict in ("DIVERGE", "AGREE_FORM_ONLY")
    assert agree.compare("t", word).sources == "whitakers+collatinus"
