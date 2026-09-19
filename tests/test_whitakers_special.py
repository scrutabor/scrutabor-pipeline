import copy
import json

import pytest
from whitakers_words.data.esse import esse
from whitakers_words.generated.uniques import uniques

from scrutabor_pipeline import agree, whitakers
from scrutabor_pipeline import whitakers_special as special


def vote(form, lemma, **morph):
    word = {"id": "w001", "form": form, "lemma": lemma, "morph": morph}
    return agree._whitakers_vote(word, morph["pos"], morph)[0]


@pytest.mark.parametrize(
    ("form", "lemma", "morph"),
    [
        (
            "est",
            "memini",
            dict(pos="verb", person=3, number="sg", tense="pres", mood="ind", voice="act"),
        ),
        (
            "memento",
            "sum",
            dict(pos="verb", person=2, number="sg", tense="pres", mood="imp", voice="act"),
        ),
        (
            "vis",
            "sum",
            dict(pos="verb", person=2, number="sg", tense="pres", mood="ind", voice="act"),
        ),
        (
            "éstque",
            "memini",
            dict(pos="verb", person=3, number="sg", tense="pres", mood="ind", voice="act"),
        ),
        ("boum", "deus", dict(pos="noun", case="gen", number="pl")),
        ("quisquis", "unusquisque", dict(pos="pron", case="nom", number="sg")),
        ("unusquisque", "quisquis", dict(pos="pron", case="nom", number="sg")),
    ],
)
def test_unrelated_special_records_cannot_confirm_each_other(form, lemma, morph):
    assert vote(form, lemma, **morph) == "FORM_MATCH"


@pytest.mark.parametrize(
    ("form", "lemma", "morph"),
    [
        (
            "est",
            "sum",
            dict(pos="verb", person=3, number="sg", tense="pres", mood="ind", voice="act"),
        ),
        (
            "éstque",
            "sum",
            dict(pos="verb", person=3, number="sg", tense="pres", mood="ind", voice="act"),
        ),
        # Provider-tense controls: not proposals to relabel the Latin future imperative.
        (
            "memento",
            "memini",
            dict(pos="verb", person=2, number="sg", tense="pres", mood="imp", voice="act"),
        ),
        (
            "mementote",
            "memini",
            dict(pos="verb", person=2, number="pl", tense="pres", mood="imp", voice="act"),
        ),
        (
            "memini",
            "memini",
            dict(pos="verb", person=1, number="sg", tense="perf", mood="ind", voice="act"),
        ),
        ("Deus", "deus", dict(pos="noun", case="voc", number="sg", gender="m")),
        ("quidquid", "quidquid", dict(pos="pron", case="acc", number="sg", gender="n")),
        ("quidquid", "quisquis", dict(pos="pron", case="acc", number="sg", gender="n")),
        ("unicuique", "unusquisque", dict(pos="pron", case="dat", number="sg")),
        ("unumquodque", "unusquisque", dict(pos="pron", case="acc", number="sg")),
        ("boves", "bos", dict(pos="noun", case="acc", number="pl")),
    ],
)
def test_reviewed_families_and_regular_records_remain_linked(form, lemma, morph):
    assert vote(form, lemma, **morph) == "CONFIRMS"


def test_special_identity_does_not_relax_morphology():
    assert (
        vote("est", "sum", pos="verb", person=2, number="sg", tense="pres", mood="ind", voice="act")
        == "CONTRADICTS"
    )
    assert (
        vote(
            "memento",
            "memini",
            pos="verb",
            person=2,
            number="sg",
            tense="fut",
            mood="imp",
            voice="act",
        )
        == "CONTRADICTS"
    )


def test_unlinked_and_absent_forms_keep_existing_status():
    assert vote("esse", "sum", pos="verb", tense="pres", mood="inf", voice="act") == "FORM_MATCH"
    assert vote("est", "unknown_head", pos="verb") == "FORM_MATCH"
    assert vote("zzzzzz", "sum", pos="verb") == "ABSENT"


def test_bare_zero_candidate_has_no_lexical_identity():
    assert whitakers.Candidate(0, "verb").identity is None
    assert whitakers.Candidate(123, "noun").identity == ("regular", 123)
    assert whitakers.Candidate(123, "noun", special_family="sum").identity == ("regular", 123)


def test_registry_binds_exact_source_records_and_reports_its_identity():
    registry = special.registry()
    provenance = registry.provenance()
    assert registry.error is None
    assert provenance["status"] == "active"
    assert provenance["actual_source_hashes"] == special.SOURCE_HASHES
    assert provenance["record_count"] == 70
    assert provenance["family_counts"] == {
        "sum": 60,
        "memini": 2,
        "deus": 1,
        "quisquis": 3,
        "unusquisque": 4,
    }
    assert len(provenance["binding_sha256"]) == 64
    reverse = special.build_registry(
        dict(reversed(list(special.SOURCE_HASHES.items()))), uniques, esse
    )
    assert json.dumps(provenance, sort_keys=True) == json.dumps(
        reverse.provenance(), sort_keys=True
    )
    with pytest.raises(TypeError):
        registry.identities["unreviewed"] = "sum"


@pytest.mark.parametrize("change", ["modified", "missing"])
def test_source_drift_disables_only_special_identity(monkeypatch, change):
    hashes = dict(special.SOURCE_HASHES)
    if change == "modified":
        hashes["data/esse.py"] = "unreviewed"
    else:
        del hashes["data/esse.py"]
    registry = special.build_registry(hashes, uniques, esse)
    assert registry.error == "special-record source drift"
    assert registry.provenance()["status"] == "inactive"
    assert registry.provenance()["binding_sha256"] is None
    monkeypatch.setattr(special, "registry", lambda: registry)
    assert (
        vote("est", "sum", pos="verb", person=3, number="sg", tense="pres", mood="ind", voice="act")
        == "FORM_MATCH"
    )
    assert (
        vote(
            "memini",
            "memini",
            pos="verb",
            person=1,
            number="sg",
            tense="perf",
            mood="ind",
            voice="act",
        )
        == "CONFIRMS"
    )
    assert vote("boves", "bos", pos="noun", case="acc", number="pl") == "CONFIRMS"
    # Formal disagreement remains visible even without a special identity.
    assert (
        vote("est", "sum", pos="verb", person=2, number="sg", tense="pres", mood="ind", voice="act")
        == "CONTRADICTS"
    )


def test_raw_signature_collision_cannot_confirm_a_family(monkeypatch):
    records = copy.deepcopy(uniques)
    other = copy.deepcopy(records["memento"][0])
    other["senses"] = ["a distinct entry with identical parser-level features"]
    records["memento"].append(other)
    registry = special.build_registry(special.SOURCE_HASHES, records, esse)
    assert registry.error == "missing or ambiguous special record"
    assert not registry.identities
    monkeypatch.setattr(special, "registry", lambda: registry)
    assert (
        vote(
            "memento",
            "memini",
            pos="verb",
            person=2,
            number="sg",
            tense="pres",
            mood="imp",
            voice="act",
        )
        == "FORM_MATCH"
    )
    assert (
        vote(
            "memini",
            "memini",
            pos="verb",
            person=1,
            number="sg",
            tense="perf",
            mood="ind",
            voice="act",
        )
        == "CONFIRMS"
    )


def test_conflicting_family_assignments_are_rejected():
    record = uniques["memento"][0]
    with pytest.raises(ValueError, match="conflicting special-record families"):
        special._bind_records([record], [("memini", record), ("sum", record)])


def test_unknown_special_record_cannot_inherit_another_identity():
    candidates = [c for c in whitakers.candidates("boum") if c.lexeme_id == 0]
    assert candidates
    assert all(c.identity is None for c in candidates)


def test_inflection_signature_is_checked_not_just_its_spelling():
    record = copy.deepcopy(uniques["memento"][0])
    record["form"][0] = "FUT"
    assert special.identity(special.UniqueInflection(record)) is None


def test_missing_optional_source_table_fails_closed_without_breaking_regulars(monkeypatch):
    read_bytes = special.Path.read_bytes

    def without_esse(path):
        if path.name == "esse.py":
            raise FileNotFoundError(path)
        return read_bytes(path)

    monkeypatch.setattr(special.Path, "read_bytes", without_esse)
    special.registry.cache_clear()
    try:
        assert special.registry().source_hashes["data/esse.py"] is None
        assert special.registry().error == "special-record source drift"
        assert (
            vote(
                "est",
                "sum",
                pos="verb",
                person=3,
                number="sg",
                tense="pres",
                mood="ind",
                voice="act",
            )
            == "FORM_MATCH"
        )
        assert vote("boves", "bos", pos="noun", case="acc", number="pl") == "CONFIRMS"
    finally:
        special.registry.cache_clear()
