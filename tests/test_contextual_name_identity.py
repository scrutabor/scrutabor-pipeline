"""Exact lexical identity boundaries; real providers, no replacement votes."""

import pytest

from scrutabor_pipeline import agree

LASALLE = "proprium.sancti-ioannis-baptistae-de-la-salle-collecta"


def noun(form, lemma, case="acc", decl=1):
    return {
        "id": "w016",
        "form": form,
        "lemma": lemma,
        "morph": {"pos": "noun", "case": case, "number": "sg", "gender": "m", "decl": decl},
    }


def test_paschal_name_does_not_inherit_adjective_identity():
    value = agree.compare(
        "proprium.sancti-paschalis-baylon-collecta", noun("Paschálem", "Paschalis", decl=3)
    )
    assert value.verdict == "EDITORIAL_ONLY"
    assert value.sources == ""
    assert "adjective" in value.detail
    assert "whitakers set aside" in value.detail
    assert "collatinus set aside" in value.detail


def test_lasalle_transferred_name_does_not_inherit_baptizer_identity():
    value = agree.compare(LASALLE, noun("Baptístam", "Baptista"))
    assert value.verdict == "EDITORIAL_ONLY"
    assert value.sources == ""
    assert "transferred" in value.detail
    assert "whitakers set aside" in value.detail
    assert "collatinus set aside" in value.detail


@pytest.mark.parametrize(
    "text",
    [
        "ordinarium.confiteor",
        "ordinarium.confiteor-sacerdotis",
        "proprium.sancti-petri-et-pauli-apostolorum-evangelium",
    ],
)
def test_same_baptist_accusative_in_literal_context_keeps_both(text):
    value = agree.compare(text, noun("Baptístam", "Baptista"))
    assert value.verdict == "AGREE"
    assert value.sources == "whitakers+collatinus"


@pytest.mark.parametrize(
    "form,lemma,case,decl,pos",
    [
        ("baptístam", "baptista", "acc", 1, "noun"),
        ("paschálem", "paschalis", "acc", 3, "adj"),
        ("Baptístæ", "Baptista", "gen", 1, "noun"),
        ("Ioánnem", "Ioannes", "acc", 3, "noun"),
    ],
)
def test_scope_does_not_change_lowercase_other_case_or_name(form, lemma, case, decl, pos):
    word = noun(form, lemma, case, decl)
    word["morph"]["pos"] = pos
    here = agree.compare(LASALLE, word)
    elsewhere = agree.compare("ordinarium.confiteor", word)
    assert (here.verdict, here.sources, here.detail) == (
        elsewhere.verdict,
        elsewhere.sources,
        elsewhere.detail,
    )
    assert here.sources == "whitakers+collatinus"


def test_existing_global_ruling_is_not_shadowed_by_text_context():
    word = noun("Felicitáte", "Felicitas", "abl", 3)
    word["morph"]["gender"] = "f"
    here = agree.compare(LASALLE, word)
    elsewhere = agree.compare("ordinarium.confiteor", word)
    assert here.verdict == elsewhere.verdict == "EDITORIAL_ONLY"
    assert here.sources == elsewhere.sources == ""
    assert here.detail == elsewhere.detail


def test_context_merges_provider_reasons_without_mutating_global(monkeypatch):
    key = "Baptista:Baptístam"
    global_reason = "Global Whitaker identity objection retained when a context adds Collatinus."
    context_reason = "Context Collatinus identity objection merges with the global Whitaker reason."
    monkeypatch.setitem(agree.CASEFOLD_HOMOGRAPH_RULINGS, key, {"whitakers": global_reason})
    monkeypatch.setitem(
        agree.CONTEXT_CASEFOLD_HOMOGRAPH_RULINGS,
        LASALLE,
        {key: {"collatinus": context_reason}},
    )
    value = agree.compare(LASALLE, noun("Baptístam", "Baptista"))
    assert value.verdict == "EDITORIAL_ONLY"
    assert value.sources == ""
    assert global_reason in value.detail and context_reason in value.detail
    assert agree.CASEFOLD_HOMOGRAPH_RULINGS[key] == {"whitakers": global_reason}


def test_all_context_identity_rulings_carry_exact_keys_and_reasons():
    contexts = agree.CONTEXT_CASEFOLD_HOMOGRAPH_RULINGS
    assert set(contexts) == {LASALLE}
    assert set(contexts[LASALLE]) == {"Baptista:Baptístam"}
    for providers in contexts[LASALLE].values():
        assert set(providers) == {"whitakers", "collatinus"}
        assert all(len(reason) > 40 for reason in providers.values())
