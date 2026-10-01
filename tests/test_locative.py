"""Keep locative transport distinct from contextual case selection."""

import pytest

from scrutabor_pipeline import collatinus, whitakers
from scrutabor_pipeline.agree import compare
from scrutabor_pipeline.feature_scopes import feature_ruling_applies


@pytest.mark.parametrize("case", ["gen", "loc"])
def test_corinthi_admits_both_cases_without_selecting_the_context(case):
    # These are both possible analyses of the spelling. Only the sentence
    # decides between a genitive dependency and a place-where locative.
    token = {
        "id": "w001",
        "form": "Corínthi",
        "lemma": "Corinthus",
        "morph": {"pos": "noun", "case": case, "number": "sg", "gender": "f", "decl": 2},
    }
    result = compare("test", token)
    assert result.verdict == "AGREE"
    assert result.sources == "whitakers+collatinus"


@pytest.mark.parametrize("case", ["nom", "dat", "acc", "abl", "voc"])
def test_corinthi_rejects_other_singular_cases(case):
    result = compare(
        "test",
        {
            "id": "w001",
            "form": "Corínthi",
            "lemma": "Corinthus",
            "morph": {"pos": "noun", "case": case, "number": "sg", "gender": "f", "decl": 2},
        },
    )
    assert result.verdict == "DIVERGE"


def test_whitaker_locative_retains_its_stated_number_and_gender():
    readings = [
        c for c in whitakers.candidates("Corínthi") if c.feature_dict().get("case") == "loc"
    ]
    assert readings
    assert all(c.feature_dict() == {"case": "loc", "number": "sg", "gender": "f"} for c in readings)


def test_collatinus_locative_does_not_invent_unstated_features():
    readings = [
        c
        for c in collatinus.candidates("Corínthi")
        if c.lemma == "corinthus" and c.feature_dict().get("case") == "loc"
    ]
    assert readings
    assert all(c.feature_dict() == {"case": "loc"} for c in readings)


@pytest.mark.parametrize(
    "key,gender", [("Israel:Israël", "m"), ("Ierusalem:Ierúsalem", "f"), ("Sion:Sion", "f")]
)
def test_locative_support_does_not_widen_indeclinable_exceptions(key, gender):
    morph = {"pos": "noun", "case": "gen", "number": "sg", "gender": gender}
    assert feature_ruling_applies(key, morph)
    assert not feature_ruling_applies(key, {**morph, "case": "loc"})
