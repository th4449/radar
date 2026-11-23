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
    assert TX.fips("Nowhere") is None
    assert TX.name("48325") == "Medina"


def test_texas_knows_all_254_counties_and_michigan_all_83():
    from pipeline.config import load_all_counties, load_counties

    every = {c.name: c.fips for c in load_all_counties("TX").counties}
    assert len(every) == 254
    for county in load_counties("TX").counties:
        assert every[county.name] == county.fips
    assert MI.fips("Washtenaw") == "26161"
    assert len(MI.mentions("Washtenaw County and Wayne County")) == 2


def test_a_text_must_say_county():
    assert TX.mentions("a site near Austin and the Hill property") == []
    (mention,) = TX.mentions("a site in Austin County")
    assert (mention.name, mention.fips, mention.in_scope) == ("Austin", "48015", True)


def test_mentions_keep_their_words_and_place():
    text = "Load additions in Hood County and TOM GREEN\nCOUNTY."
    out = TX.mentions(text)
    assert [(m.name, m.fips) for m in out] == [("Hood", "48221"), ("Tom Green", "48451")]
    assert all(text[m.start : m.end] == m.text for m in out)


def test_a_county_outside_the_test_set_is_seen_and_marked_out_of_scope():
    out = TX.mentions("The STEC Medina County Large Load Project, Western Medina County")
    assert [(m.name, m.fips, m.in_scope) for m in out] == [("Medina", "48325", False)] * 2


def test_a_list_of_counties_names_each_one():
    # The wording of a real ERCOT planning file.
    text = "reliability in Bexar and Medina counties with the addition of 2 GW"
    out = TX.mentions(text)
    assert [(m.name, m.in_scope) for m in out] == [("Bexar", True), ("Medina", False)]
    assert [text[m.start : m.end] for m in out] == ["Bexar", "Medina"]
    out = TX.mentions("Hood, Somervell, and Erath Counties")
    assert [m.name for m in out] == ["Hood", "Somervell", "Erath"]
    assert [m.name for m in TX.mentions("Hood & Tom Green counties")] == ["Hood", "Tom Green"]


def test_headings_and_ordinary_words_before_county_are_not_a_county():
    # "Project Name Tier Project ISD County(s)" is a table heading in the same real file.
    assert TX.mentions("TPIT Project Name Tier Project ISD County(s)") == []
    assert TX.mentions("The County will hold a hearing. Each County may adopt rules.") == []
    assert TX.mentions("several counties") == []
    assert [m.name for m in TX.mentions("In Travis County")] == ["Travis"]


def test_a_longer_county_name_is_not_cut_short():
    assert [m.name for m in TX.mentions("San Saba County")] == ["San Saba"]
    assert [m.name for m in TX.mentions("Jim Wells County and Wells Fargo")] == ["Jim Wells"]


# --- the backtest's control counties -------------------------------------------------------------


def test_the_control_counties_are_eleven_real_counties_outside_the_thirty():
    from pipeline.config import load_all_counties, load_control_counties, load_counties

    controls = load_control_counties("TX").counties
    assert [c.name for c in controls] == [
        "Lamb", "Comanche", "Eastland", "Lampasas", "Mills", "Wood", "Titus", "Colorado",
        "Lavaca", "Runnels", "Coleman",
    ]  # fmt: skip
    every = {c.name: c.fips for c in load_all_counties("TX").counties}
    assert all(every[c.name] == c.fips for c in controls)
    assert not {c.fips for c in controls} & load_counties("TX").fips_set


def test_no_known_project_sits_in_a_control_county():
    from backtest.projects import load_known_projects
    from pipeline.config import load_control_counties

    controls = {c.name for c in load_control_counties("TX").counties}
    assert not [p.key for p in load_known_projects() if p.county in controls]
