"""The measurement behind the /editio page's one statistic.

The page tells a reader that over three fifths of the edition's words have an
ambiguous form and that María admits twelve readings. Both numbers are taken
from `ambiguity.measure`, and this test pins the shape of the measure so that
a change to it is a deliberate change rather than a drift in a sentence
nobody re-reads.
"""

from scrutabor_pipeline.ambiguity import parses


def test_maria_admits_twelve_readings():
    # The page's own example, and the reason it was chosen: a short proper
    # name whose form is one of the most ambiguous in the corpus.
    assert len(parses("María")) == 12


def test_an_unambiguous_form_counts_once():
    # sæculórum is genitive plural and nothing else.
    assert len(parses("sæculórum")) == 1


def test_a_form_the_analyzer_does_not_know_counts_zero():
    # Melchísedech is one of the 50 forms Whitaker's carries no entry for —
    # mostly proper names of the Canon's saints, plus a handful of syncopated
    # perfects. They are counted apart from the ambiguous ones, not with them.
    assert parses("Melchísedech") == set()
