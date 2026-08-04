"""Normalize liturgical display forms into analyzer queries.

The corpus stores 1962 liturgical orthography (accents, j for consonantal i,
ligatures, diaeresis — see the corpus repo's ORTHOGRAPHY.md); analyzers and
dictionaries expect classical normalized spellings. Derived mechanically,
never stored.
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
