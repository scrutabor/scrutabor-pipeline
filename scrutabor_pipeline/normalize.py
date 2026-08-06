"""Normalize liturgical display forms into analyzer queries.

The corpus stores 1962 liturgical orthography (accents, i for consonantal i,
ligatures, diaeresis — see the corpus repo's ORTHOGRAPHY.md); analyzers and
dictionaries expect classical normalized spellings. Derived mechanically,
never stored.

The two analyzers do not want the same spelling of the glide, so the query
is per-analyzer: `analyzer_query` for Collatinus, `whitakers_query` for
Whitaker's. See the comment on GLIDE_PREFIXES.
"""

import unicodedata

LIGATURES = {"æ": "ae", "œ": "oe", "Æ": "Ae", "Œ": "Oe", "ǽ": "ae", "Ǽ": "Ae"}

# Liturgical spellings whose dictionary heads differ — recorded here so the
# divergence is expected, never silent. Applied as prefix rewrites so every
# inflected form maps: quotidiánum -> cotidianum.
SPELLING_PREFIXES = [
    ("quotidian", "cotidian"),
    ("tentati", "temptati"),
]


def strip_accents(text: str) -> str:
    out = []
    for ch in unicodedata.normalize("NFD", text):
        if unicodedata.category(ch) != "Mn":
            out.append(ch)
    return unicodedata.normalize("NFC", "".join(out))


def analyzer_query(form: str) -> str:
    """Display form or lemma -> the spelling an analyzer expects."""
    text = strip_accents(form)
    for k, v in LIGATURES.items():
        text = text.replace(k, v)
    text = text.lower().replace("j", "i")
    for liturgical, classical in SPELLING_PREFIXES:
        if text.startswith(liturgical):
            text = classical + text[len(liturgical):]
    return text


VOWELS = frozenset("aeiouy")

# Whitaker's dictionary heads the consonant as j — jubeo, justus, majestas,
# Jesus, Joannes — and returns NOTHING when the query spells it i, which is
# what this module used to send it. Collatinus folds i and j together and is
# indifferent. So the glide is written back to j for Whitaker's alone.
#
# Consonantal i stands between vowels (eius), at the head of a word before
# another vowel (Iesus, iube), and across the seam of a compound whose
# simplex begins with it (ad-iutorium). Prefix and stem must both be named,
# because the same position holds a VOCALIC i in the compounds of eo (ab-iit)
# — the tables are the corpus's, from checks/normalize.py, where the same
# rule decides syllable counts.
GLIDE_PREFIXES = frozenset(
    ("ab", "ad", "con", "de", "dis", "in", "inter", "ob", "per", "prae", "sub", "trans")
)
GLIDE_STEMS = ("iac", "iect", "iud", "iung", "iunct", "iur", "iust", "iut", "iuv")


def _after_prefix(text: str, at: int) -> bool:
    return text[:at] in GLIDE_PREFIXES and text[at:].startswith(GLIDE_STEMS)


def whitakers_query(form: str) -> str:
    """The analyzer query with the consonantal i written as j, which is how
    Whitaker's dictionary spells it."""
    text = analyzer_query(form)
    out: list[str] = []
    prev_vowel = False
    for i, ch in enumerate(text):
        nxt = text[i + 1] if i + 1 < len(text) else ""
        # qu/gu before a vowel is a glide, not a vowel: the i of quia has no
        # vowel before it and stays vocalic.
        if ch == "u" and out and out[-1] in "qg" and nxt in VOWELS:
            out.append(ch)
            prev_vowel = False
            continue
        if ch == "i" and nxt in VOWELS and (prev_vowel or i == 0 or _after_prefix(text, i)):
            out.append("j")
            prev_vowel = False
            continue
        out.append(ch)
        prev_vowel = ch in VOWELS
    return "".join(out)
