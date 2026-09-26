"""The source-agreement rule: is the corpus's editorial analysis among the
candidates each independent analyzer proposes for the same form?

Each analyzer votes separately:
- CONFIRMS      proposes our exact reading under our dictionary entry
- FORM_MATCH    proposes our reading, but under an entry that could not be
                linked to our lemma
- CONTRADICTS   knows the form but proposes no reading matching ours
- ABSENT        does not know the form

Combined verdict for a token:
- DIVERGE          any analyzer contradicts — review queue material
- AGREE            no contradiction, at least one analyzer confirms
                   (detail names which)
- AGREE_RULED      as AGREE, but one analyzer's contradiction was set aside
                   by a recorded ruling (FEATURE_RULINGS) — counted apart so
                   an adjudicated token never hides inside a clean number
- AGREE_FORM_ONLY  no contradiction, only form-level matches
- FORM_ABSENT      no analyzer knows the form
- EDITORIAL_ONLY   the only analyzer that knows the form was set aside by a
                   ruling, so nothing machine-checkable remains — the parse
                   rests on the edition alone and says so in its provenance
"""

from dataclasses import dataclass

from . import collatinus, whitakers
from .normalize import analyzer_query

# Recorded classification rulings (corpus SCHEMA.md, TERMINOLOGY decisions):
# our part of speech on the left may match these analyzer parts of speech.
POS_RULINGS: dict[str, set[str]] = {
    # sicut is tagged conj in the corpus; several dictionaries head it as
    # an adverb. Whitaker's proposes both, so this ruling is usually moot,
    # but it is recorded so a CONJ-less candidate set stays an expected
    # divergence, not a silent one.
    "conj": {"conj", "adv"},
    # amen (and other indeclinable Hebrew loans) are intj in the corpus;
    # Whitaker's classes them as adverbs.
    "intj": {"intj", "adv"},
    # prohibitive ne is adv in the corpus (a reviewed ruling); Whitaker's
    # heads it as conj/adv.
    "adv": {"adv", "conj"},
}

# Lemma spellings the analyzers dictionary as separate or fused entries:
# our lemma on the left, every analyzer entry that IS the same word on the
# right.
LEMMA_ALIASES: dict[str, tuple[str, ...]] = {
    "ab": ("a", "ab"),  # Whitaker's carries a and ab as two entries
    "tu": ("tu", "tecum"),  # Collatinus dictionaries the fused tecum itself
    # Lewis and Short, dextera: both spellings name the feminine noun.
    # Collatinus heads it under dextra; dexterus is a distinct adjective.
    "dextera": ("dextera", "dextra"),
    # Homograph discriminators (corpus SCHEMA.md): the key carries the part of
    # speech, the analyzers are asked about the word itself.
    "hic_adverbium": ("hic",),
    "caligo_nomen": ("caligo",),
    "clam_adverbium": ("clam",),
    "supra_adverbium": ("supra",),
    "foris_adverbium": ("foris",),  # outside, distinct from foris the door
    "dico_dedicare": ("dico",),  # dedicate, first conjugation, not dicere (say)
    "volo_volare": ("volo",),  # fly, first conjugation, not velle (wish)
    "labor_labi": ("labor",),  # deponent labi, not the noun laboris
    "mundus_purus": ("mundus",),  # clean, not the noun meaning world
    "inimicus_hostilis": ("inimicus",),  # hostile adjective, not the enemy noun
    "adversus_prep": ("adversus",),
    "sero_adverb": ("sero",),
    "infernus_inferior": ("infernus",),
    "amare_adverb": ("amare", "amarus"),
    # The Advent IV gospel's `in libro`, discriminated from liber the adjective
    # (free). Without the alias the underscore key reached Whitaker's as a
    # word, and the whole comparison raised rather than returning a verdict --
    # so the agreement report and the review queue could not be produced at
    # all from 2026-08-18, the day that text landed.
    "liber_volumen": ("liber",),
    # Verb homographs split by quantity: occído kill / óccido fall, set;
    # excído cut out / éxcido fall away; and the deponent furor, furári
    # (steal) beside the noun furor, furóris (rage).
    "occido_cado": ("occido",),
    "excido_cado": ("excido",),
    "furor_nomen": ("furor",),
    # Collatinus dictionaries the fused id+ipsum as one lemma (as it does
    # tecum, three lines up); the corpus lemmatizes the pronoun under idem
    # and lets the fusion be the form's business.
    "idem": ("idem", "idipsum"),
    "memini": ("memini", "memento"),  # Collatinus heads the imperative itself
    # Collatinus heads the adjective under its archaic nominative saluos,
    # which the u/v fold of salvus (saluus) cannot reach. Both analyzers
    # do read the word; only the spelling of the head differs.
    "salvus": ("salvus", "salvos"),
}


def link_spellings(lemma: str) -> tuple[str, ...]:
    """The dictionary spellings a lemma may be linked under.

    A discriminated key (liber_volumen) is the corpus's own notation, not a
    Latin word, and SCHEMA.md requires it to carry an alias above. When the
    alias is missing, the honest answer is NO spellings: the analyzers then
    fail to link the lemma and the verdict says so — instead of the raw
    underscore key reaching Whitaker's as a word and the whole report dying
    on it, which is how the machine sat unrunnable from 2026-08-18 while
    thirty texts landed, and how it would have died again on the next such
    key with only the one alias added.
    """
    if lemma in LEMMA_ALIASES:
        return LEMMA_ALIASES[lemma]
    if "_" in lemma:
        return ()
    return (lemma,)


# Lemmas no analyzer carries, each with the reason. An absent form under one
# of these is expected, not a finding.
EXPECTED_ABSENT: dict[str, str] = {
    # Martyrs of the Canon whose names are in neither analyzer's lexicon. The
    # genitive of each is secure from the chain of genitives it stands in;
    # only the dictionaries are silent.
    "Cletus": "pope and martyr of the Communicantes; in neither lexicon",
    "Cosmas": "martyr of the Communicantes; in neither lexicon",
    "Damianus": "martyr of the Communicantes; in neither lexicon",
}

# Contradictions already adjudicated: the named analyzer is demonstrably
# wrong about this form, or models it differently from us in a way we have
# reasoned through. Keyed "<lemma>:<form>" on the corpus's own spelling.
#
# A ruling makes that ONE analyzer abstain — it never invents a
# confirmation. If the other analyzer does not confirm, the token still
# does not reach AGREE, and the report counts ruled tokens separately so
# they can never hide inside a clean number. Every entry carries the
# reason it was accepted; that reason is the whole value of the mechanism.
FEATURE_RULINGS: dict[str, dict[str, str]] = {
    "quaeso:quǽsumus": {
        "collatinus": (
            "reads the fossilised parenthetical as its own lemma and tags it "
            "3rd singular; the form is the 1st plural of quaeso, as Whitaker's "
            "and every grammar have it"
        )
    },
    "vos:vobíscum": {
        "collatinus": (
            "dictionaries the fused vobis+cum as one lemma and tags it "
            "singular; the enclitic attaches to a plural ablative (cf. the "
            "tu/tecum alias above)"
        )
    },
    "vos:vestri": {
        "collatinus": (
            "vestri is a genitive plural of the personal pronoun vos, distinct from "
            "inflections of the possessive vester. Collatinus links this form only to "
            "the possessive. Choosing the personal pronoun is a contextual editorial "
            "decision, not established by this ruling; confirmation still requires "
            "another analyzer's actual vote"
        )
    },
    "nos:nostri": {
        "collatinus": (
            "nostri is a genitive plural of the personal pronoun nos, distinct from "
            "inflections of the possessive noster. Collatinus links this form only to "
            "the possessive. Choosing the personal pronoun is a contextual editorial "
            "decision, not established by this ruling; confirmation still requires "
            "another analyzer's actual vote"
        )
    },
    # --- the Canon ---
    "refrigerium:refrigérii": {
        "whitakers": (
            "carries THIS ENTRY with the contracted genitive singular alone (refrigeri) and "
            "so reads the uncontracted refrigérii as a locative. Not a rule about -ium "
            "nouns: the same analyzer reads Evangélii as a genitive singular. Lewis and "
            "Short head the noun refrigerium, ii, three coordinate genitives leave a "
            "locative no room, and Collatinus confirms the genitive"
        )
    },
    "clemens:clementíssime": {
        "whitakers": (
            "offers only the superlative ADVERB for this form; clementíssime Pater is the "
            "vocative agreeing with Pater, which Collatinus heads and confirms"
        )
    },
    "martyr:Mártyrum": {
        "whitakers": (
            "returns genitive SINGULAR for mártyrum, a number the form cannot carry (the "
            "genitive singular is mártyris) — a porting artefact; Collatinus gives the "
            "genitive plural the series of plural genitives requires"
        )
    },
    "martyr:mártyrum": {
        "whitakers": (
            "returns genitive SINGULAR for mártyrum, a number the form cannot carry (the "
            "genitive singular is mártyris) — a porting artefact; Collatinus gives the "
            "genitive plural the series of plural genitives requires"
        )
    },
    "memini:Meménto": {
        "whitakers": (
            "tags the form present; meménto is the FUTURE imperative, and the only imperative "
            "memini has. Collatinus agrees on the tense under its own lemma. Omitting the "
            "tense would have satisfied both analyzers by claiming less than is known"
        )
    },
    "fio:fíeri": {
        "collatinus": (
            "reads the present infinitive as an imperative; fíeri is the infinitive of fio, "
            "as its own dictionary head (fio, fíeri, factus sum) and Whitaker's have it, and "
            "fio has no passive imperative"
        )
    },
    "sanctificator:sanctificátor": {
        "whitakers": (
            "carries no agent noun sanctificator and reads the -tor ending as the archaic "
            "future passive imperative of sanctifico; the word is the Christian-Latin noun "
            "sanctificátor, sanctificatóris, which Collatinus heads and confirms"
        )
    },
    "filius:Fílii": {
        "whitakers": (
            "carries THIS ENTRY with the contracted genitive singular alone (fili) and "
            "so reads filii as plural or locative. Not a rule about -ius nouns: the "
            "same analyzer reads Evangélii as a genitive singular, and does not carry "
            "Cornelii or Laurentii at all. The uncontracted filii is the genitive "
            "throughout the Vulgate and the liturgical books, the genitive chains of "
            "the Canon admit nothing else, and Collatinus confirms it"
        )
    },
    "pressura:pressúra": {
        "whitakers": (
            "misclassifies the nominative singular noun pressura as a verbal form of presso; "
            "Collatinus confirms the noun, and the Vulgate text and surrounding syntax require "
            "it as the subject of erit"
        )
    },
    "Israel:Israël": {
        "whitakers": (
            "treats the indeclinable proper name as nominative or vocative only; the corpus "
            "reads it in the case its own syntax requires — the object of rédimet in the "
            "psalm, and plebis tuæ Israël standing in apposition to a genitive in the Advent "
            "alleluia — while Collatinus leaves the case open. The reason once argued only "
            "the accusative and the ruling outgrew it; it is a rule about the analyzer's "
            "closed case list, not about one verse"
        )
    },
    "Israel:Ísrael": {
        "whitakers": (
            "treats this spelling of the indeclinable proper name as nominative or "
            "vocative only; the dative beneficiary in bonus Israel Deus rectis corde "
            "is established by the clause, while Collatinus leaves the case open. "
            "This is the same closed-case-list limitation as Israel:Israël, not "
            "independent analyzer proof of the dative"
        )
    },
    "Aaron:Áaron": {
        "collatinus": (
            "enumerates the indeclinable name as nominative or vocative only; in barbam "
            "barbam Áaron (Ps 132:2) the name is the genitive, the same closed case list "
            "as Israel:Israël"
        )
    },
    "Simeon:Símeon": {
        "collatinus": (
            "enumerates the indeclinable name as nominative or vocative only; Ex tribu "
            "Símeon (Apoc 7:7), like every tribe name in the list around it, is the genitive"
        )
    },
    "Iuda:Iuda": {
        "collatinus": (
            "enumerates the indeclinable name as nominative, vocative or ablative only; in ex "
            "tribu Iuda (Apoc 7:5) and de tribu Iuda the tribe's name is the genitive, as the "
            "Greek Ἰούδα is"
        )
    },
    "abyssus:abýssus": {
        "whitakers": (
            "offers only the nominative; in Cor Iesu, virtútum ómnium abýssus the title stands "
            "in apposition to the addressed Heart, a Greek feminine in -us used for its vocative"
        ),
        "collatinus": "the same: nominative alone, where the litany addresses the Heart",
    },
    "Abraham:Ábrahæ": {
        "collatinus": (
            "gives the first-declension Ábrahæ as the genitive alone, while the ending is "
            "the dative as well: Quam olim Ábrahæ promisísti (to Abraham) and Ábrahæ dictæ "
            "sunt promissiónes (Gal 3:16) are datives. Whitaker's does not carry the name"
        )
    },
    "unusquisque:unumquódque": {
        "whitakers": (
            "its table of the unus-quisque compound gives unumquodque only as a masculine "
            "accusative, which the form cannot be (that is unumquemque); unumquódque is the "
            "neuter nominative and accusative singular, as Collatinus has it, and in "
            "unumquódque eórum ... ambulábat (Ezek 1:12) it is the subject"
        )
    },
    "summus:summæ": {
        "whitakers": (
            "reads summæ only as the noun summa; in uníus summæ divinitátis "
            "partícipes it is the superlative adjective agreeing with divinitátis, "
            "as Collatinus has it"
        )
    },
    "praedicator:prædicátor": {
        "whitakers": (
            "offers only the future passive imperative of prǽdico; in éxstitit "
            "prædicátor et rector the word is the noun, coordinated with rector, "
            "as Collatinus has it"
        )
    },
    "consilium:consílii": {
        "whitakers": (
            "offers only a locative for the uncontracted form; consílii is the genitive "
            "singular required by boni and magni in the two litany invocations, and "
            "Collatinus confirms it"
        )
    },
    "oboediens:obœdientíssime": {
        "whitakers": (
            "offers only an adverb, while the form is the masculine vocative superlative "
            "agreeing with Iesu; Collatinus confirms the adjective"
        )
    },
    "zelator:zelátor": {
        "whitakers": (
            "has no agent noun zelator and misreads its vocative as a future passive "
            "imperative; Collatinus confirms the noun used in apposition to Iesu"
        )
    },
    # --- the Advent divergences, adjudicated 2026-08-19 ---
    # Nineteen tokens sat in the review queue from the day the machine came
    # back up. Read against the grammar and the analyzers' live output, every
    # one is a case where the edition is right and a dictionary is short.
    "meus:meus": {
        "whitakers": (
            "offers only the nominative; meus in address stands in the vocative, as in "
            "Deus meus, the Psalter's address (Ps 21:2 and throughout), beside the "
            "nominative-for-vocative Deus, and in pópule meus (Ps 77:1), where the "
            "classical paradigm's mi never appears in these books"
        ),
        "collatinus": (
            "the same: nominative alone, the classical mi expected for the vocative. The "
            "form of address the liturgy actually prints is meus, at every one of its "
            "occurrences here"
        ),
    },
    "dominus:Dóminus": {
        "whitakers": (
            "offers only the nominative; in Dómine Dóminus noster (Ps 8:2) the form "
            "stands in apposition to the vocative Dómine and is itself the address, the "
            "nominative-for-vocative the Psalter also uses for Deus and meus"
        ),
        "collatinus": (
            "the same: nominative alone; the verse addresses the Lord twice, and the "
            "second title shares the case of the first"
        ),
    },
    "Ierusalem:Ierúsalem": {
        "whitakers": (
            "heads the city neuter (the Hierosolyma, -orum tradition) and contradicts the "
            "feminine; the indeclinable singular name is feminine in the scriptures' own "
            "concord — quæ occídis prophétas (Mt 23:37) — and in the vocative here "
            "(Ierúsalem, surge)"
        )
    },
    "solatium:solátii": {
        "whitakers": (
            "the contracted-genitive defect of refrigérii and consílii above, at another "
            "-ium noun: it carries the entry with the contracted genitive alone and reads "
            "the uncontracted solátii as a locative. Deus patiéntiæ et solátii is a pair "
            "of coordinate genitives, and Collatinus confirms the second"
        )
    },
    "imperium:impérii": {
        "whitakers": (
            "the same contracted-genitive defect: anno quintodécimo impérii Tibérii "
            "Cǽsaris is a chain of genitives dating the year, and a locative has no place "
            "in it. Collatinus confirms the genitive"
        )
    },
    "Tiberius:Tibérii": {
        "whitakers": (
            "the same defect on the emperor's name: it reads the uncontracted genitive as "
            "a locative or a plural. One Tiberius, whose reign the verse dates; Collatinus "
            "confirms the genitive singular"
        )
    },
    "exeo:exístis": {
        "whitakers": (
            "reads the form as a present of exsisto; exístis in Mt 11:7-9 (quid exístis "
            "in desértum vidére) is the contracted perfect of exeo — exi(v)istis, 'what "
            "went ye out to see' — as the received rendering of every age has it, and "
            "Collatinus confirms exactly that: exeo, perfect, second plural"
        )
    },
    "Sion:Sion": {
        "collatinus": (
            "enumerates the indeclinable name in three cases only (nominative, vocative, "
            "accusative); the Psalter's own constructions put it in the rest — ex Sion an "
            "ablative, pópulus Sion a genitive. An indeclinable serves every case, and a "
            "closed list of three is the dictionary's economy, not the word's limit"
        )
    },
    "manifeste:maniféste": {
        "whitakers": (
            "carries only the adjective manifestus, whose vocative shares this surface; "
            "between subject and verb (Deus maniféste véniet) the word is the adverb in "
            "-e, which Collatinus heads and confirms"
        )
    },
    "idem:idípsum": {
        "whitakers": (
            "offers only its adverb idipsum ('at once', the Ps 4:9 idiom); in det vobis "
            "idípsum sápere (Rom 15:5) the fused id+ipsum is the object of sápere — 'to "
            "mind the same thing' — the pronoun, as the whole exegetical tradition of ut "
            "idem sapiátis reads it. Collatinus dictionaries the fusion itself (aliased "
            "above)"
        )
    },
    "alteruter:altérutrum": {
        "whitakers": (
            "files the compound under adjective and adverb; the corpus files the "
            "uter-compounds as pronouns, as it files uter and alter themselves, and in "
            "altérutrum (Rom 15:5) is the pronoun after in. Collatinus confirms the "
            "accusative neuter under the same head"
        )
    },
    "credo:credéndo": {
        "whitakers": (
            "models the gerund as its gerundive and returns future passive readings; in "
            "credéndo (Rom 15:13) is the ablative gerund — believing, not to-be-believed "
            "— the reading SCHEMA.md's own gerund note reserves a ruling for. Collatinus "
            "confirms the ablative under credo"
        )
    },
    "pecco:peccándo": {
        "whitakers": (
            "models this gerund as its gerundive and returns future passive readings; "
            "peccándo names the act by which the speaker deserved punishment and offended "
            "God, so it is the ablative gerund, not a future passive participle. Collatinus "
            "confirms the ablative gerund under pecco"
        )
    },
    "veneror:venerándo": {
        "whitakers": (
            "models this gerund as a future passive gerundive. In the Seven Sorrows "
            "collect, dolores eius venerando recolimus, venerando expresses the "
            "manner of commemoration; no ablative nominal licenses gerundive "
            "agreement. Deponents have active gerunds. Collatinus confirms the "
            "ablative gerund under veneror; the attested collateral venero is not "
            "thereby rejected as a Latin verb"
        )
    },
    "pecco:peccandíque": {
        "whitakers": (
            "models the enclitic-bearing gerund as its gerundive and returns future passive "
            "readings; peccandí is the genitive gerund governed by occasiones, while -que "
            "coordinates the second object of the resolution. Collatinus confirms the "
            "genitive gerund under pecco"
        )
    },
    "summus:summum": {
        "whitakers": (
            "offers noun readings alone, but summum directly modifies the substantival "
            "neuter bonum in summum bonum, both standing in accusative apposition to te. "
            "The agreement and phrase syntax require the superlative adjective, which "
            "Collatinus confirms under summus"
        )
    },
    "summus:summis": {
        "whitakers": (
            "offers noun summa/summum readings alone. In reconcilians ima summis "
            "(Annunciation Paschal Alleluia), the lower things are reconciled with "
            "the upper: summis is a substantivized superlative adjective in the "
            "neuter dative plural. Lewis and Short, summus/superus and reconcilio, "
            "support the adjective and accusative-plus-dative construction; "
            "Collatinus confirms the adjective form under summus"
        )
    },
    "proximus:próximas": {
        "whitakers": (
            "offers only the second-person verb proximo, but próximas agrees with the "
            "feminine accusative plural noun occasiónes in the established phrase "
            "occasiones proximas. The syntax requires the adjective, which Collatinus "
            "confirms under proximus"
        )
    },
    "Annas:Anna": {
        "whitakers": (
            "knows the surface only as the imperative of annáre, to swim toward — a "
            "caseless homograph, not the high priest (Lc 3:2). The name declines Annas, "
            "Annæ like the Greek masculines beside it in the verse, and the ablative "
            "stands in the same absolute as Cáipha two words on"
        )
    },
    # --- adverbs Whitaker's carries only as adjective or numeral forms ---
    "stricte:stricte": {
        "whitakers": (
            "offers only the vocative of strictus; in Cuncta stricte discussúrus the word "
            "qualifies the participle (the judge who will examine all things strictly), the "
            "adverb Lewis and Short give under strictus"
        )
    },
    "mystice:mýstice": {
        "whitakers": (
            "offers only the vocative of mysticus; in quæ sub oblátis munéribus mýstice "
            "designántur the word qualifies the verb (signified mystically), the adverb of "
            "the Christian writers"
        )
    },
    "iniuste:iniúste": {
        "whitakers": (
            "offers only the vocative of iniustus; in tradébat autem iudicánti se iniúste "
            "(1 Pt 2:23, the Vulgate's reading) the word qualifies the participle, to him "
            "who judged him unjustly"
        )
    },
    "pacifice:pacífice": {
        "whitakers": (
            "offers only the vocative of pacificus; in mundi cursus pacífice nobis tuo "
            "órdine dirigátur the word qualifies the verb (be directed peacefully), the "
            "adverb Collatinus heads"
        )
    },
    "pie:pie": {
        "whitakers": (
            "offers only vocatives, of pius and of the name Pius; in sóbrie et iuste et pie "
            "vivámus (Tit 2:12) and Fac me tecum pie flere the word is the adverb, as "
            "Collatinus heads it"
        )
    },
    "prospere:próspere": {
        "whitakers": (
            "offers only the vocative of prosperus; in inténde, próspere procéde, et regna "
            "(Ps 44:5) the word qualifies the imperative (go forward prosperously)"
        )
    },
    "valide:válide": {
        "whitakers": (
            "offers only the vocative of validus; in Crucifíxi fige plagas cordi meo válide "
            "the word qualifies the imperative (fix them firmly), the adverb Lewis and Short "
            "give under validus. Collatinus reads the form under the contracted valde"
        )
    },
    "multifariam:Multifárie": {
        "whitakers": (
            "offers only the vocative of an adjective; Multifárie olim Deus loquens (Heb 1:1 "
            "in the Christmas octave Alleluia) is the adverb, in many ways, the -e variant "
            "of multifariam"
        )
    },
    "semel:semel": {
        "whitakers": (
            "files the numeral adverb under its numeral and reports it as an adjective "
            "without case; semel (once) qualifies the verb in every occurrence here "
            "(introívit semel, mórtuus est semel, semel lapidátus sum)"
        )
    },
    "bis:bis": {
        "whitakers": (
            "files the numeral adverb under its numeral and reports it as an adjective "
            "without case; in Ieiúno bis in sábbato bis (twice) qualifies the verb"
        )
    },
    "quinquies:quínquies": {
        "whitakers": (
            "files the numeral adverb under its numeral and reports it as an adjective "
            "without case; in A Iudǽis quínquies quadragénas una minus accépi the word "
            "(five times) qualifies the verb"
        )
    },
    # --- gender ---
    "villicatio:villicatiónis": {
        "whitakers": (
            "carries villicatio as masculine; like every -tio abstract, and as Lewis and "
            "Short head it (villicatio, onis, f.), the noun is feminine"
        )
    },
    "villicatio:villicatiónem": {
        "whitakers": (
            "carries villicatio as masculine; like every -tio abstract, and as Lewis and "
            "Short head it (villicatio, onis, f.), the noun is feminine"
        )
    },
    "villicatio:villicatióne": {
        "whitakers": (
            "carries villicatio as masculine; like every -tio abstract, and as Lewis and "
            "Short head it (villicatio, onis, f.), the noun is feminine"
        )
    },
}

# Proper names whose normalized spelling is identical to an ordinary Latin
# dictionary word. The analyzers are case-blind, so a formally matching parse
# of the common noun or adjective cannot confirm the identity of the saint's
# name. The named analyzer abstains from any opinion based on that homograph;
# the same lowercase common word remains fully machine-checkable.
CASEFOLD_HOMOGRAPH_RULINGS: dict[str, dict[str, str]] = {
    "Felicitas:Felicitáte": {
        "whitakers": (
            "carries the common noun felicitas (happiness), not the martyr Felicitas; its "
            "case-folded noun parse cannot establish the proper name"
        ),
        "collatinus": (
            "likewise carries the common noun felicitas rather than the martyr's name; the "
            "matching inflection does not establish lexical identity"
        ),
    },
    # Moved here from FEATURE_RULINGS on 2026-08-19: their old reasons credited
    # Collatinus with "confirming the name" on the strength of the very
    # common-word homographs this table exists to refuse — its Lini candidates
    # are the flax words, its Clemens the adjective. The standard is one
    # standard: a case-folded common word establishes no saint's name, from
    # either analyzer, and the parses rest on the edition (the genitives are
    # secure from the chain of genitives each stands in).
    "Linus:Lini": {
        "whitakers": (
            "carries no pope Linus — only linum (flax) and lino — and reads the case-folded "
            "name as one of them; that match cannot establish the proper name"
        ),
        "collatinus": (
            "likewise heads only lino, linum and their kin at this surface; a flax-word "
            "parse cannot establish the pope's name"
        ),
    },
    "Clemens:Cleméntis": {
        "whitakers": (
            "carries only the adjective clemens, not the pope's name; the adjective's "
            "genitive cannot establish it"
        ),
        "collatinus": (
            "likewise offers the adjective clemens (and clementia); the same formal match "
            "the rule above refuses from Whitaker's cannot count as the name from here"
        ),
    },
    "Perpetua:Perpétua": {
        "whitakers": (
            "carries no martyr Perpetua and reads the case-folded name as the adjective "
            "perpetuus; that formal match cannot establish the proper name"
        ),
        "collatinus": (
            "likewise heads only perpetuus/perpetuum, not the martyr Perpetua; its "
            "case-folded adjective parse cannot establish lexical identity"
        ),
    },
}

# Features the corpus stores that the comparison checks when an analyzer
# offers an opinion on them. decl/conj and `governs` are editorial-level
# (not exposed comparably by the adapters).
COMPARED = ("case", "number", "gender", "person", "tense", "mood", "voice", "degree")


@dataclass
class Verdict:
    token_ref: str  # "<text-id>.<word-id>"
    verdict: str
    sources: str = ""  # analyzers that confirmed, "+"-joined
    detail: str = ""


def _features_match(ours: dict, theirs: dict) -> bool:
    for key in COMPARED:
        our_value = ours.get(key)
        their_value = theirs.get(key)
        if our_value is None or their_value is None:
            continue  # one side has no opinion — compatible
        if key == "voice" and our_value == "dep":
            # Deponency is a lemma-level fact the analyzers vocabularize
            # differently: Whitaker's reports the passive FORM, Collatinus
            # the active MEANING. Lemma identity is checked separately, so
            # the voice tag itself is not compared for deponents.
            continue
        if our_value != their_value:
            return False
    return True


def _pos_match(our_pos: str, candidate_pos: str) -> bool:
    return candidate_pos == our_pos or candidate_pos in POS_RULINGS.get(our_pos, set())


def _whitakers_class_gap(form: str, ours: dict, theirs: dict) -> str | None:
    """A reading Whitaker's tables cannot give, recognized by what they print instead.

    It has no gerund: every -nd- form comes back as the gerundive (the future
    passive participle), whose neuter singular in the oblique cases is the
    gerund's own form. And its tables give the -ii genitive singular of
    second-declension nouns in -ius and -ium (sacrifícii, iudícii, fílii) only
    as a locative, a case these nouns do not have in use. In both cases the
    analyzer is set aside, never counted as confirming: it cannot tell the
    gerund from the gerundive, and it does not print the genitive at all.
    """
    if ours.get("mood") == "ger":
        if (
            theirs.get("tense") == "fut"
            and theirs.get("voice") == "pass"
            and theirs.get("case") == ours.get("case")
            and theirs.get("number") == "sg"
            and theirs.get("gender") == "n"
        ):
            return (
                "has no gerund and prints the form as the gerundive of the same case, "
                "whose neuter singular is the gerund's form"
            )
        return None
    if (
        ours.get("case") == "gen"
        and ours.get("number") == "sg"
        and theirs.get("case") == "loc"
        and theirs.get("number") == "sg"
        and theirs.get("gender") in (None, ours.get("gender"))
        and analyzer_query(form).endswith("ii")
    ):
        return (
            "gives the -ii genitive singular of a second-declension noun only as a "
            "locative, a case the noun does not have in use"
        )
    return None


def _whitakers_vote(word: dict, our_pos: str, ours: dict) -> tuple[str, str]:
    cands = whitakers.candidates(word["form"])
    if not cands:
        return "ABSENT", ""
    matching = [
        c for c in cands if _pos_match(our_pos, c.pos) and _features_match(ours, c.feature_dict())
    ]
    if not matching:
        for c in cands:
            gap = _pos_match(our_pos, c.pos) and _whitakers_class_gap(
                word["form"], ours, c.feature_dict()
            )
            if gap:
                return "CLASS_GAP", gap
        proposals = sorted({f"{c.pos}:{c.feature_dict()}" for c in cands})
        return "CONTRADICTS", f"whitakers proposes {proposals[:6]}"
    identities = {
        c.identity
        for spelling in link_spellings(word["lemma"])
        for c in whitakers.lemma_candidates(spelling)
        if c.identity is not None and _pos_match(our_pos, c.pos)
    }
    if any(c.identity in identities for c in matching):
        return "CONFIRMS", ""
    return "FORM_MATCH", f"whitakers cannot link lemma {word['lemma']!r}"


def _collatinus_vote(word: dict, our_pos: str, ours: dict) -> tuple[str, str]:
    cands = collatinus.candidates(word["form"])
    if not cands:
        return "ABSENT", ""
    matching = [c for c in cands if _features_match(ours, c.feature_dict())]
    if not matching:
        proposals = sorted({f"{c.lemma}:{c.feature_dict()}" for c in cands})
        return "CONTRADICTS", f"collatinus proposes {proposals[:6]}"
    accepted = {collatinus.fold_lemma(spelling) for spelling in link_spellings(word["lemma"])}
    if any(c.lemma in accepted for c in matching):
        return "CONFIRMS", ""
    return "FORM_MATCH", f"collatinus reads it under {sorted({c.lemma for c in matching})[:4]}"


def compare(text_id: str, word: dict) -> Verdict:
    ref = f"{text_id}.{word['id']}"
    ours = dict(word["morph"])
    our_pos = ours.pop("pos")

    votes = {
        "whitakers": _whitakers_vote(word, our_pos, ours),
        "collatinus": _collatinus_vote(word, our_pos, ours),
    }

    key = f"{word['lemma']}:{word['form']}"

    # A case-blind dictionary match to an ordinary word does not establish a
    # capitalized proper name. Set that named analyzer's opinion aside whether
    # it called the common-word parse matching or contradictory; this never
    # affects the lowercase lexeme.
    identity_rulings = CASEFOLD_HOMOGRAPH_RULINGS.get(key, {})
    ruled = [
        f"{name} set aside: {reason}"
        for name, reason in identity_rulings.items()
        if votes.get(name, ("", ""))[0] in {"CONFIRMS", "FORM_MATCH", "CONTRADICTS"}
    ]
    for name in identity_rulings:
        if votes.get(name, ("", ""))[0] in {"CONFIRMS", "FORM_MATCH", "CONTRADICTS"}:
            votes[name] = ("ABSTAINS", "")

    # A reading the analyzer's tables cannot give at all is set aside the same
    # way, for the whole class, with the reason (see _whitakers_class_gap).
    for name, (vote, reason) in list(votes.items()):
        if vote == "CLASS_GAP":
            ruled.append(f"{name} set aside: {reason}")
            votes[name] = ("ABSTAINS", "")

    # An adjudicated contradiction abstains instead of counting against us,
    # and the token is reported as ruled rather than as plain agreement.
    rulings = FEATURE_RULINGS.get(key, {})
    ruled.extend(
        f"{name} set aside: {reason}"
        for name, reason in rulings.items()
        if votes.get(name, ("", ""))[0] == "CONTRADICTS"
    )
    for name in rulings:
        if votes.get(name, ("", ""))[0] == "CONTRADICTS":
            votes[name] = ("ABSTAINS", "")

    # Overall agreement and individual confirmations are separate facts.
    # Preserve a real confirmation even when the other analyzer disagrees;
    # the disagreement still remains in the review queue.
    confirming = [name for name, (v, _) in votes.items() if v == "CONFIRMS"]
    contradictions = [f"{d}" for v, d in votes.values() if v == "CONTRADICTS"]
    if contradictions:
        return Verdict(
            ref,
            "DIVERGE",
            sources="+".join(confirming),
            detail=f"ours={our_pos}:{ours} | " + " | ".join(contradictions),
        )

    if confirming:
        if ruled:
            return Verdict(
                ref, "AGREE_RULED", sources="+".join(confirming), detail="; ".join(ruled)
            )
        return Verdict(ref, "AGREE", sources="+".join(confirming))

    form_matches = [d for v, d in votes.values() if v == "FORM_MATCH"]
    if form_matches:
        return Verdict(ref, "AGREE_FORM_ONLY", detail="; ".join(form_matches))

    # A ruling set the only opinion aside: say that, rather than claim the
    # form is unknown — it is known, and we judged it wrong.
    if ruled:
        return Verdict(
            ref,
            "EDITORIAL_ONLY",
            detail=f"no analyzer confirms {word['form']!r} — " + "; ".join(ruled),
        )
    lemma = word["lemma"]
    if lemma in EXPECTED_ABSENT:
        return Verdict(ref, "FORM_ABSENT", detail=f"expected: {EXPECTED_ABSENT[lemma]}")
    return Verdict(ref, "FORM_ABSENT", detail=f"form {word['form']!r} unknown to every analyzer")
