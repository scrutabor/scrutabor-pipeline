"""A disagreement does not erase another analyzer's actual confirmation."""

import json

import pytest

from scrutabor_pipeline import agree, agreement


def companion():
    return {
        "id": "w001",
        "form": "consórtium",
        "lemma": "consors",
        "morph": {"pos": "noun", "case": "gen", "number": "pl", "gender": "m", "decl": 3},
    }


def test_personal_companions_preserve_confirmation_and_disagreement():
    result = agree.compare("proprium.example", companion())
    assert result.verdict == "DIVERGE"
    assert result.sources == "whitakers"
    assert "collatinus proposes" in result.detail
    assert "consortium" in result.detail


@pytest.mark.parametrize("confirming", ["whitakers", "collatinus"])
def test_each_analyzers_confirmation_survives_the_others_contradiction(monkeypatch, confirming):
    for name in ("whitakers", "collatinus"):
        vote = ("CONFIRMS", "") if name == confirming else ("CONTRADICTS", f"{name} disagrees")
        monkeypatch.setattr(agree, f"_{name}_vote", lambda *_args, vote=vote: vote)
    result = agree.compare("proprium.example", companion())
    assert result.verdict == "DIVERGE"
    assert result.sources == confirming
    assert "disagrees" in result.detail


@pytest.mark.parametrize("claims_both", [False, True])
def test_strict_provenance_names_only_the_analyzer_that_confirms(tmp_path, capsys, claims_both):
    source = tmp_path / "texts" / "proprium"
    source.mkdir(parents=True)
    claims = ["editorial", "whitakers"] + (["collatinus"] if claims_both else [])
    document = {
        "id": "proprium.example",
        "segments": [{"id": "s01", "words": [companion()]}],
        "editorial": {"analysis_defaults_words": {"sources": claims, "review": "pending"}},
    }
    (source / "example.json").write_text(json.dumps(document), encoding="utf-8")
    assert agreement.main(["agreement", "--strict", str(tmp_path)]) == (1 if claims_both else 0)
    output = capsys.readouterr().out
    assert "DIVERGE" in output
    assert "queue=1" in output
    assert f"provenance_mismatch={int(claims_both)}" in output


def test_an_impossible_case_still_has_no_confirming_sources():
    token = companion()
    token["morph"]["case"] = "dat"
    result = agree.compare("proprium.example", token)
    assert result.verdict == "DIVERGE"
    assert result.sources == ""
