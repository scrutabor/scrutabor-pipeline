"""Grammatical limits of the per-form exceptions documented in agree.py.

These are exception scopes, not a replacement morphological dictionary or
contextual verdict. A new reading outside a scope must face the analyzers;
it must not inherit an exception solely by sharing a lemma and spelling.
Absent features are deliberately absent, rather than wildcards. decl/conj
and governs remain outside the analyzer comparison, as in agree.COMPARED.
"""

type Value = str | int | None
type Scope = dict[str, tuple[Value, ...]]

FEATURES = ("pos", "case", "number", "gender", "person", "tense", "mood", "voice", "degree")
CASES = ("nom", "gen", "dat", "acc", "abl", "voc")


def scope(**features: Value | tuple[Value, ...]) -> Scope:
    return {key: value if isinstance(value, tuple) else (value,) for key, value in features.items()}


def nominal(
    pos: str,
    case: str | tuple[str, ...],
    number: str,
    gender: str | tuple[str, ...],
    degree: Value | tuple[Value, ...] = None,
) -> Scope:
    return scope(pos=pos, case=case, number=number, gender=gender, degree=degree)


# A scope covers only the reading argued by the corresponding reason. Where
# the reason concerns a whole indeclinable case list, all six cases are open,
# but number, gender and part of speech are not. Distinct combinations stay
# separate (e.g. intimus); Cartesian combinations must not invent readings.
FEATURE_SCOPES: dict[str, tuple[Scope, ...]] = {
    "quaeso:quǽsumus": (
        scope(pos="verb", person=1, number="pl", tense="pres", mood="ind", voice="act"),
    ),
    "quaeso:Quǽsumus": (
        scope(pos="verb", person=1, number="pl", tense="pres", mood="ind", voice="act"),
    ),
    "vos:vobíscum": (scope(pos="pron", case="abl", number="pl"),),
    "vos:vestri": (scope(pos="pron", case="gen", number="pl"),),
    "nos:nostri": (scope(pos="pron", case="gen", number="pl"),),
    "refrigerium:refrigérii": (nominal("noun", "gen", "sg", "n"),),
    "clemens:clementíssime": (nominal("adj", "voc", "sg", "m", "sup"),),
    "martyr:Mártyrum": (nominal("noun", "gen", "pl", "m"),),
    "martyr:mártyrum": (nominal("noun", "gen", "pl", "m"),),
    "memini:Meménto": (
        scope(pos="verb", person=2, number="sg", tense="fut", mood="imp", voice="act"),
    ),
    "memini:meménto": (
        scope(pos="verb", person=2, number="sg", tense="fut", mood="imp", voice="act"),
    ),
    "memini:Mementóte": (
        scope(pos="verb", person=2, number="pl", tense="fut", mood="imp", voice="act"),
    ),
    "fio:fíeri": (scope(pos="verb", tense="pres", mood="inf", voice="act"),),
    "sanctificator:sanctificátor": (nominal("noun", ("nom", "voc"), "sg", "m"),),
    "filius:Fílii": (nominal("noun", "gen", "sg", "m"),),
    "pressura:pressúra": (nominal("noun", "nom", "sg", "f"),),
    "Israel:Israël": (nominal("noun", CASES, "sg", "m"),),
    "Israel:Ísrael": (nominal("noun", CASES, "sg", "m"),),
    "Aaron:Áaron": (nominal("noun", "gen", "sg", "m"),),
    "Simeon:Símeon": (nominal("noun", "gen", "sg", "m"),),
    "Iuda:Iuda": (nominal("noun", "gen", "sg", "m"),),
    "abyssus:abýssus": (nominal("noun", "voc", "sg", "f"),),
    "Abraham:Ábrahæ": (nominal("noun", "dat", "sg", "m"),),
    "unusquisque:unumquódque": (nominal("pron", ("nom", "acc"), "sg", "n"),),
    # The corpus sometimes leaves a lexical superlative's degree unstated.
    # This exception allows omission or sup, never pos/comp.
    "summus:summæ": (nominal("adj", "gen", "sg", "f", (None, "sup")),),
    "praedicator:prædicátor": (nominal("noun", "nom", "sg", "m"),),
    "consilium:consílii": (nominal("noun", "gen", "sg", "n"),),
    "oboediens:obœdientíssime": (nominal("adj", "voc", "sg", "m", "sup"),),
    "zelator:zelátor": (nominal("noun", "voc", "sg", "m"),),
    "meus:meus": (nominal("adj", "voc", "sg", "m"),),
    "dominus:Dóminus": (nominal("noun", "voc", "sg", "m"),),
    "Ierusalem:Ierúsalem": (nominal("noun", CASES, "sg", "f"),),
    "solatium:solátii": (nominal("noun", "gen", "sg", "n"),),
    "imperium:impérii": (nominal("noun", "gen", "sg", "n"),),
    "Tiberius:Tibérii": (nominal("noun", "gen", "sg", "m"),),
    "exeo:exístis": (
        scope(pos="verb", person=2, number="pl", tense="perf", mood="ind", voice="act"),
    ),
    "Sion:Sion": (nominal("noun", CASES, "sg", "f"),),
    "manifeste:maniféste": (scope(pos="adv"),),
    "idem:idípsum": (nominal("pron", "acc", "sg", "n"),),
    "alteruter:altérutrum": (nominal("pron", "acc", "sg", "n"),),
    "credo:credéndo": (
        scope(
            pos="verb", case="abl", number="sg", gender="n", tense="pres", mood="ger", voice="act"
        ),
    ),
    "pecco:peccándo": (
        scope(
            pos="verb", case="abl", number="sg", gender="n", tense="pres", mood="ger", voice="act"
        ),
    ),
    "veneror:venerándo": (
        scope(
            pos="verb", case="abl", number="sg", gender="n", tense="pres", mood="ger", voice="act"
        ),
    ),
    "pecco:peccandíque": (
        scope(
            pos="verb", case="gen", number="sg", gender="n", tense="pres", mood="ger", voice="act"
        ),
    ),
    "summus:summum": (nominal("adj", "acc", "sg", "n", "sup"),),
    "summus:summis": (nominal("adj", "dat", "pl", "n", "sup"),),
    "proximus:próximas": (nominal("adj", "acc", "pl", "f", (None, "sup")),),
    "Annas:Anna": (nominal("noun", "abl", "sg", "m"),),
    "stricte:stricte": (scope(pos="adv"),),
    "mystice:mýstice": (scope(pos="adv"),),
    "iniuste:iniúste": (scope(pos="adv"),),
    "pacifice:pacífice": (scope(pos="adv"),),
    "pie:pie": (scope(pos="adv"),),
    "prospere:próspere": (scope(pos="adv"),),
    "valide:válide": (scope(pos="adv"),),
    "multifariam:Multifárie": (scope(pos="adv"),),
    "semel:semel": (scope(pos="adv"),),
    "bis:bis": (scope(pos="adv"),),
    "quinquies:quínquies": (scope(pos="adv"),),
    "villicatio:villicatiónis": (nominal("noun", "gen", "sg", "f"),),
    "villicatio:villicatiónem": (nominal("noun", "acc", "sg", "f"),),
    "villicatio:villicatióne": (nominal("noun", "abl", "sg", "f"),),
    "pascha:Pascha": (nominal("noun", ("nom", "acc"), "sg", "n"),),
    "poenitens:pæniténtibus": (nominal("adj", "dat", "pl", "m"),),
    "butyrum:Butýrum": (nominal("noun", "acc", "sg", "n"),),
    "prior:prior": (nominal("adj", "nom", "sg", "m", "comp"),),
    "prior:prióri": (nominal("adj", "abl", "sg", "n", "comp"),),
    "prior:prióribus": (nominal("adj", "abl", "pl", "n", "comp"),),
    "prior:priórem": (nominal("adj", "acc", "sg", "m", "comp"),),
    "sum:futúrus": (
        scope(
            pos="verb", case="nom", number="sg", gender="m", tense="fut", mood="part", voice="act"
        ),
    ),
    "manna:manna": (nominal("noun", ("nom", "acc"), "sg", "n"),),
    "duodenus:duodénæ": (nominal("adj", "dat", "sg", "f"),),
    "mille:mille": (nominal("adj", "nom", "pl", "m"),),
    "fractura:fractúra": (nominal("noun", "nom", "sg", "f"),),
    "temptator:tentátor": (nominal("noun", "nom", "sg", "m"),),
    "mediator:mediátor": (nominal("noun", "nom", "sg", "m"),),
    "daemonium:dæmónium": (nominal("noun", "acc", "sg", "n"),),
    "summus:summo": (nominal("adj", "abl", "sg", ("m", "n"), (None, "sup")),),
    "idipsum:Idípsum": (nominal("pron", "acc", "sg", "n"),),
    "idipsum:idípsum": (nominal("pron", "acc", "sg", "n"),),
    "quidam:quædam": (nominal("adj", "nom", "sg", "f"),),
    "pressura:pressúræ": (nominal("noun", "gen", "sg", "f"),),
    "vidua:vídua": (nominal("noun", "nom", "sg", "f"),),
    "vidua:víduas": (nominal("noun", "acc", "pl", "f"),),
    "proximus:próximum": (
        nominal("adj", "acc", "sg", "m", (None, "sup")),
        nominal("adj", "nom", "sg", "n", (None, "sup")),
    ),
    "proximus:próximi": (nominal("adj", "gen", "sg", "m", (None, "sup")),),
    "proximus:próximus": (nominal("adj", "nom", "sg", "m", (None, "sup")),),
    "proximus:próximo": (nominal("adj", "abl", "sg", "m", (None, "sup")),),
    "proximus:próximos": (nominal("adj", "acc", "pl", "m", (None, "sup")),),
    "intimus:íntima": (
        nominal("adj", "acc", "pl", "n", (None, "sup")),
        nominal("adj", "abl", "sg", "f", (None, "sup")),
    ),
    "vetus:véteri": (nominal("adj", "abl", "sg", "n"),),
    "exeo:exísti": (
        scope(pos="verb", person=2, number="sg", tense="perf", mood="ind", voice="act"),
    ),
    "satum:satis": (nominal("noun", "abl", "pl", "n"),),
    "ficus:ficus": (nominal("noun", "acc", "pl", "f"), nominal("noun", "nom", "sg", "f")),
    "sufficientia:sufficiéntia": (nominal("noun", "nom", "sg", "f"),),
    "secta:sectæ": (nominal("noun", "nom", "pl", "f"),),
    "Iustus:Iustus": (nominal("noun", "nom", "sg", "m"),),
    "virgo:vírgines": (nominal("noun", "nom", "pl", "m"),),
    "huiusmodi:huiúsmodi": (
        nominal("pron", ("acc", "abl"), "sg", "m"),
        nominal("pron", "acc", "pl", "n"),
    ),
    "interior:interiórem": (nominal("adj", "acc", "sg", "m", "comp"),),
    "fluxus:fluxum": (nominal("noun", "acc", "sg", "m"),),
    "Saba:Saba": (nominal("noun", "gen", "sg", "f"),),
    "aether:ǽthera": (nominal("noun", "acc", "sg", "m"),),
    "Phares:Phares": (nominal("noun", ("nom", "acc"), "sg", "m"),),
    "Aram:Aram": (nominal("noun", ("nom", "acc"), "sg", "m"),),
    "Eleazar:Eleázar": (nominal("noun", "acc", "sg", "m"),),
    "potens:Potens": (nominal("adj", "nom", "sg", "n"),),
    "Iona:Iona": (nominal("noun", "gen", "sg", "m"),),
    "consors:consórtium": (nominal("noun", "gen", "pl", "m"),),
    "vos:vos": (scope(pos="pron", case="voc", number="pl"),),
    "abstergo:abstérget": (
        scope(pos="verb", person=3, number="sg", tense="fut", mood="ind", voice="act"),
    ),
    "mediator:Mediátor": (nominal("noun", "nom", "sg", "m"),),
    "Aser:Aser": (nominal("noun", "gen", "sg", "m"),),
    "Zabulon:Zábulon": (nominal("noun", "gen", "sg", "m"),),
    "Manasses:Manásse": (nominal("noun", "gen", "sg", "m"),),
    "sum:fúerint": (
        scope(pos="verb", person=3, number="pl", tense="futperf", mood="ind", voice="act"),
    ),
    "secundo_adverbium:secúndo": (scope(pos="adv"),),
    "supra_adverbium:supérius": (scope(pos="adv", degree="comp"),),
}


def feature_ruling_applies(key: str, morph: dict) -> bool:
    """Only the documented morphology can set an analyzer's contradiction aside."""
    return any(
        all(morph.get(feature) in candidate.get(feature, (None,)) for feature in FEATURES)
        for candidate in FEATURE_SCOPES.get(key, ())
    )
