"""Equivalent noun spellings must not borrow confirmation from adjectives."""

import pytest

from scrutabor_pipeline import agree, collatinus


def right_hand(case="nom", number="sg", gender="f", lemma="dextera"):
    return {
        "id": "w001",
        "form": "déxtera",
        "lemma": lemma,
        "morph": {"pos": "noun", "case": case, "number": number, "gender": gender, "decl": 1},
    }


def test_same_noun_spelling_is_confirmed_by_both_analyzers():
    result = agree.compare("t", right_hand())
    assert result.verdict == "AGREE"
    assert result.sources == "whitakers+collatinus"
    assert agree.link_spellings("dextera") == ("dextera", "dextra")


@pytest.mark.parametrize("case", ["gen", "dat"])
def test_noun_alias_does_not_hide_an_impossible_case(case):
    result = agree.compare("t", right_hand(case))
    assert result.verdict == "DIVERGE"
    assert result.sources == ""


def test_collatinus_adjective_readings_cannot_confirm_a_neuter_plural_noun():
    result = agree.compare("t", right_hand(number="pl", gender="n"))
    assert "collatinus" not in result.sources


def test_an_unrelated_noun_cannot_borrow_the_right_hand_reading():
    result = agree.compare("t", right_hand(lemma="manus"))
    assert result.sources == ""


def test_removing_the_noun_candidate_removes_collatinus_confirmation(monkeypatch):
    original = collatinus.candidates
    monkeypatch.setattr(
        collatinus,
        "candidates",
        lambda form: [c for c in original(form) if c.lemma != "dextra"],
    )
    result = agree.compare("t", right_hand())
    assert result.sources == "whitakers"
