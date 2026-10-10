from copy import deepcopy

import pytest

from scrutabor_pipeline import agree
from scrutabor_pipeline.feature_scopes import FEATURE_SCOPES, FEATURES, feature_ruling_applies


def token():
    return {
        "id": "w202",
        "form": "Damásci",
        "lemma": "Damascus",
        "morph": {"pos": "noun", "case": "loc", "number": "sg", "gender": "f", "decl": 2},
    }


def test_city_locative_reports_editorial_basis_not_machine_confirmation(monkeypatch):
    word = token()
    result = agree.compare("t", word)
    assert result.verdict == "EDITORIAL_ONLY"
    assert result.sources == ""
    assert "whitakers set aside" in result.detail
    assert "collatinus set aside" in result.detail
    ruling = agree.FEATURE_RULINGS["Damascus:Damásci"]
    monkeypatch.delitem(agree.FEATURE_RULINGS, "Damascus:Damásci")
    assert agree.compare("t", word).verdict == "DIVERGE"
    monkeypatch.setitem(agree.FEATURE_RULINGS, "Damascus:Damásci", ruling)
    assert agree.compare("t", word) == result


@pytest.mark.parametrize("provider", ["whitakers", "collatinus"])
def test_each_contradicting_provider_needs_its_own_reason(monkeypatch, provider):
    rule = deepcopy(agree.FEATURE_RULINGS["Damascus:Damásci"])
    del rule[provider]
    monkeypatch.setitem(agree.FEATURE_RULINGS, "Damascus:Damásci", rule)
    result = agree.compare("t", token())
    assert result.verdict == "DIVERGE"
    assert result.sources == ""


def test_city_ruling_does_not_erase_supported_genitive_or_other_readings():
    for case, gender in [("gen", "m"), ("gen", "f"), ("loc", "m")]:
        word = token()
        word["morph"].update(case=case, gender=gender)
        assert not feature_ruling_applies("Damascus:Damásci", word["morph"])
        result = agree.compare("t", word)
        assert result.verdict == ("AGREE" if (case, gender) == ("gen", "m") else "DIVERGE")
        assert "set aside" not in result.detail


def test_exact_identity_scope_does_not_cover_other_lemma_or_form(monkeypatch):
    for provider in ("whitakers", "collatinus"):
        monkeypatch.setattr(agree, f"_{provider}_vote", lambda *args: ("CONTRADICTS", "control"))
    assert agree.compare("t", token()).verdict == "EDITORIAL_ONLY"
    for field, value in [("form", "Damasci"), ("lemma", "damascus"), ("form", "Damáscus")]:
        word = token()
        word[field] = value
        assert agree.compare("t", word).verdict == "DIVERGE"


def test_city_scope_is_exact_even_when_dictionary_coverage_is_removed(monkeypatch):
    for provider in ("whitakers", "collatinus"):
        monkeypatch.setattr(agree, f"_{provider}_vote", lambda *args: ("CONTRADICTS", "control"))
    healthy = token()
    assert agree.compare("t", healthy).verdict == "EDITORIAL_ONLY"
    replacements = {
        "pos": (None, "adj", "verb"),
        "case": (None, "nom", "gen", "dat", "acc", "abl", "voc"),
        "number": (None, "pl"),
        "gender": (None, "m", "n"),
        "person": (1,),
        "tense": ("pres",),
        "mood": ("ind",),
        "voice": ("act",),
        "degree": ("pos",),
    }
    assert set(replacements) == set(FEATURES)
    for feature, values in replacements.items():
        for value in values:
            word = deepcopy(healthy)
            word["morph"][feature] = value
            assert not feature_ruling_applies("Damascus:Damásci", word["morph"])
            assert agree.compare("t", word).verdict == "DIVERGE"
            assert agree.compare("t", healthy).verdict == "EDITORIAL_ONLY"
    scope = FEATURE_SCOPES.pop("Damascus:Damásci")
    try:
        assert agree.compare("t", healthy).verdict == "DIVERGE"
    finally:
        FEATURE_SCOPES["Damascus:Damásci"] = scope
    assert agree.compare("t", healthy).verdict == "EDITORIAL_ONLY"
