"""County assignment from a county column and from the words in a text."""

from __future__ import annotations

from pipeline.counties import CountyIndex

TX = CountyIndex.for_state("TX")
MI = CountyIndex.for_state("MI")


def test_a_county_column_gives_the_code():
    assert TX.fips("Hood") == "48221"
    assert TX.fips("HOOD") == "48221"
    assert TX.fips(" Tom  Green County ") == "48451"
    assert TX.name("48221") == "Hood"


def test_a_county_outside_the_test_set_has_no_code():
    assert TX.fips("Medina") is None
    assert TX.fips("") is None


def test_michigan_holds_every_county():
    assert MI.fips("Washtenaw") == "26161"
    assert len(MI.mentions("Washtenaw County and Wayne County")) == 2


def test_a_text_must_say_county():
    assert TX.mentions("a site near Austin and the Hill property") == []
    (mention,) = TX.mentions("a site in Austin County")
    assert (mention.name, mention.fips) == ("Austin", "48015")


def test_mentions_keep_their_words_and_place():
    text = "Load additions in Hood County and TOM GREEN\nCOUNTY."
    out = TX.mentions(text)
    assert [(m.name, m.fips) for m in out] == [("Hood", "48221"), ("Tom Green", "48451")]
    assert all(text[m.start : m.end] == m.text for m in out)


def test_a_county_outside_the_test_set_is_still_seen_as_a_county():
    out = TX.mentions("The STEC Medina County Large Load Project, Western Medina County")
    assert [(m.name, m.fips) for m in out] == [("Medina", None), ("Medina", None)]


def test_ordinary_words_before_county_are_not_a_name():
    assert TX.mentions("The County will hold a hearing. Each County may adopt rules.") == []
    assert [m.name for m in TX.mentions("In Travis County")] == ["Travis"]


def test_a_configured_county_is_not_also_read_as_an_unknown_one():
    out = TX.mentions("Southeast Travis County")
    assert [(m.name, m.fips) for m in out] == [("Travis", "48453")]
