import pathlib

from scrutabor_pipeline import collatinus, compat
from scrutabor_pipeline.collatinus import candidates, fold_lemma, parse_morph


def test_parse_morph_maps_french_vocabulary():
    assert parse_morph("2ème singulier subjonctif présent actif") == {
        "person": 2,
        "number": "sg",
        "mood": "subj",
        "tense": "pres",
        "voice": "act",
    }
    assert parse_morph("vocatif singulier") == {"case": "voc", "number": "sg"}
    assert parse_morph("ablatif féminin pluriel") == {
        "case": "abl",
        "gender": "f",
        "number": "pl",
    }


def test_parse_morph_reads_the_compound_tenses_as_the_backend_writes_them():
    # Both strings are the backend's own, and this test asserted an invented
    # one until 2026-08-19: it spelled the pluperfect out, which the data
    # file never does in a morph string, so the mapping it proved was a
    # mapping nothing could reach. The future perfect is two words whose
    # first would otherwise map to the plain future, so order matters there
    # and nowhere else.
    assert parse_morph("3ème singulier subjonctif PQP actif")["tense"] == "plup"
    assert parse_morph("3ème singulier indicatif futur antérieur actif")["tense"] == "futperf"
    assert parse_morph("3ème singulier indicatif futur actif")["tense"] == "fut"


def test_parse_morph_indeclinable_is_open():
    assert parse_morph("-") == {}


def test_fold_lemma_bridges_orthographies():
    # Collatinus lemmatizes in classical u-style and may number homonyms
    assert fold_lemma("aveo") == fold_lemma("aueo")
    assert fold_lemma("Ioannes") == fold_lemma("Joannes")
    assert fold_lemma("dico2") == fold_lemma("dico")
    assert fold_lemma("quotidianus") == fold_lemma("cotidianus")


def test_collatinus_knows_the_hebrew_proper_names():
    michael = candidates("Michaéli")
    assert any(c.lemma == "michael" and c.feature_dict().get("case") == "dat" for c in michael)
    iesus = candidates("Jesus")
    assert any(c.lemma == "iesus" for c in iesus)


def test_collatinus_reads_liturgical_orthography_via_normalization():
    cands = candidates("sǽcula")
    assert any(c.lemma == "saeculum" and c.feature_dict().get("case") == "acc" for c in cands)


def test_parse_morph_maps_participle():
    from scrutabor_pipeline.collatinus import parse_morph

    features = parse_morph("participe parfait passif accusatif masculin singulier")
    assert features == {
        "mood": "part",
        "tense": "perf",
        "voice": "pass",
        "case": "acc",
        "gender": "m",
        "number": "sg",
    }


# --- the tables may hold no dead key --------------------------------------


def morph_strings() -> list[str]:
    """Every morph string the backend can emit, read the way its own loader
    reads them: numbered lines, stopping at the first line without a colon.

    That is where the data file's trailing list of feature NAMES begins — a
    glossary the loader never reaches, so a word that occurs only there is
    not vocabulary, it is documentation.
    """
    compat.apply()
    import pycollatinus.parser

    data = pathlib.Path(pycollatinus.parser.__file__).parent / "data" / "morphos.fr"
    strings = []
    for line in data.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("!"):
            continue
        if ":" not in line:
            break
        strings.append(line.split(":", 1)[1])
    return strings


def test_every_mapping_key_occurs_in_a_morph_string_the_backend_emits():
    """PHRASES expected `plus-que-parfait` until 2026-08-19, and the twelve
    strings that state the pluperfect all abbreviate it PQP — so the tense
    was dropped from every pluperfect Collatinus read, while the spelled-out
    phrase sat in the file's glossary looking like proof that it was not.
    """
    strings = morph_strings()
    assert strings, "no morph strings read — the check would pass on nothing"
    for phrase, _ in collatinus.PHRASES:
        assert any(phrase in s for s in strings), f"{phrase!r}: no morph string contains it"
    for token in collatinus.TOKENS:
        assert any(token in s.split() for s in strings), f"{token!r}: no morph string uses it"


# --- one certain reading per mapped value ---------------------------------

# (form, feature, mapped value, what makes the reading certain). A mutation
# study on 2026-08-19 corrupted génitif, locatif, neutre, 3ème, imparfait,
# impératif, infinitif, comparatif and superlatif one at a time and the whole
# suite stayed green; each of them is claimed by a form here now.
FEATURE_ORACLES = [
    ("credéndo", "mood", "ger", "the ablative gerund of credo (Rom 15:13, in credéndo)"),
    ("glóriæ", "case", "gen", "genitive singular of gloria"),
    ("domi", "case", "loc", "the locative of domus, which this backend states alone"),
    ("mirabílius", "gender", "n", "neuter comparative of mirabilis"),
    ("venit", "person", 3, "third singular of venio"),
    ("erat", "tense", "impf", "imperfect of sum"),
    ("fúerant", "tense", "plup", "indicative pluperfect of sum"),
    ("audivísset", "tense", "plup", "subjunctive pluperfect of audio"),
    ("veni", "mood", "imp", "singular imperative of venio"),
    ("esse", "mood", "inf", "present infinitive of sum"),
    ("purióres", "degree", "comp", "comparative of purus"),
    ("Altíssimus", "degree", "sup", "superlative of altus"),
]


def test_each_mapped_feature_value_is_reached_by_a_form_that_carries_it():
    for form, feature, value, why in FEATURE_ORACLES:
        offered = {c.feature_dict().get(feature) for c in candidates(form)}
        assert value in offered, (
            f"{form} ({why}): no candidate with {feature}={value}, got {offered}"
        )
