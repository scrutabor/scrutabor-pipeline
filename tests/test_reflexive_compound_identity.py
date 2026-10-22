"""The two reflexive compound entries cannot confirm one another by form alone."""

from copy import deepcopy

import pytest

from scrutabor_pipeline import agree, whitakers


@pytest.mark.parametrize(
    ("lemma", "identity"),
    [("seipse", ("regular", 34615)), ("semetipse", ("regular", 34656))],
    ids=["short", "met"],
)
def test_dictionary_heads_retain_distinct_real_identities(lemma, identity):
    assert agree.link_spellings(lemma) == (lemma,)
    candidates = whitakers.lemma_candidates(lemma)
    assert candidates
    assert {candidate.identity for candidate in candidates} == {identity}
    assert all(candidate.pos == "pron" for candidate in candidates)


@pytest.mark.parametrize(
    ("form", "lemma", "case", "gender"),
    [
        ("seípsum", "seipse", "acc", "m"),
        ("seípsum", "seipse", "acc", "n"),
        ("semetípsum", "semetipse", "acc", "m"),
        ("semetípso", "semetipse", "abl", "m"),
    ],
    ids=["short-m", "short-n", "met-acc", "met-abl"],
)
def test_actual_vote_confirms_only_the_matching_entry_and_case(form, lemma, case, gender):
    morph = {"pos": "pron", "case": case, "number": "sg", "gender": gender}
    token = {"id": "w001", "form": form, "lemma": lemma, "morph": morph}
    original = deepcopy(token)
    features = {key: value for key, value in morph.items() if key != "pos"}
    assert agree._whitakers_vote(token, "pron", features) == ("CONFIRMS", "")
    crossed = deepcopy(token)
    crossed["lemma"] = "semetipse" if lemma == "seipse" else "seipse"
    assert agree._whitakers_vote(crossed, "pron", features) == (
        "FORM_MATCH",
        f"whitakers cannot link lemma {crossed['lemma']!r}",
    )
    wrong_case = deepcopy(token)
    wrong_case["morph"]["case"] = "dat"
    assert case != "dat"
    vote, detail = agree._whitakers_vote(wrong_case, "pron", {**features, "case": "dat"})
    assert vote == "CONTRADICTS"
    assert detail.startswith("whitakers proposes ")
    assert agree._whitakers_vote(token, "pron", features) == ("CONFIRMS", "")
    assert token == original
