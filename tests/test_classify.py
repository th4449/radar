"""Keyword rules: what counts as a hit, and what does not."""

from __future__ import annotations

from pipeline.classify import KeywordRules, snippet, strongest

RULES = KeywordRules()


def kinds_and_terms(text: str) -> list[tuple[str, str]]:
    return [(h.kind, h.term) for h in RULES.find(text)]


def test_direct_terms_match_whole_words_in_any_case():
    assert kinds_and_terms("A new Data Center is proposed.") == [("direct_term", "data center")]
    assert kinds_and_terms("DATACENTER campus") == [("direct_term", "datacenter")]
    assert kinds_and_terms("two data centres") == [("direct_term", "data centre")]


def test_a_plural_counts_and_a_longer_word_does_not():
    assert kinds_and_terms("data centers and technology campuses") == [
        ("direct_term", "data center"),
        ("code_word", "technology campus"),
    ]
    assert kinds_and_terms("metadata centering") == []
    assert kinds_and_terms("a large loader") == []


def test_a_term_broken_across_a_line_or_joined_by_a_hyphen_still_matches():
    hits = RULES.find("the proposed data\ncenter and a large-load customer")
    assert [(h.term, h.text) for h in hits] == [
        ("data center", "data\ncenter"),
        ("large load", "large-load"),
    ]


def test_every_code_word_in_the_plan_is_found():
    text = (
        "Rezone to light industrial for a data processing use on a technology campus under a "
        "development agreement. The large load needs a reinvestment zone and a special land use."
    )
    assert [h.term for h in RULES.find(text)] == [
        "light industrial", "data processing", "technology campus", "development agreement",
        "large load", "reinvestment zone", "special land use",
    ]  # fmt: skip
    assert {h.kind for h in RULES.find(text)} == {"code_word"}


def test_a_project_code_name_is_found_and_ordinary_phrases_are_not():
    hits = RULES.find("Project Falcon was discussed. The Project Manager gave a Project Update.")
    assert [(h.kind, h.term) for h in hits] == [("project_code_name", "Project Falcon")]


def test_phrases_seen_in_real_records_are_not_code_names():
    # A city's well address, a company's legal form and a planning file's column headings.
    for text in (
        "Street Reconstruction Project Between Example Rd and Example Ave",
        "Drainage Project Intersection of Example St",
        "I 40 Example Interchange Project LLC",
        "TPIT Project Name Tier Project ISD County(s)",
        "Project COD Capacity (~MW)",
    ):
        assert kinds_and_terms(text) == [], text
    assert kinds_and_terms("soil borings for Project Toaster") == [
        ("project_code_name", "Project Toaster")
    ]


def test_a_code_name_keeps_its_place_in_the_text():
    text = "Item 7: Project\nBlue-Jay incentives"
    (hit,) = RULES.find(text)
    assert hit.term == "Project Blue-Jay"
    assert text[hit.start : hit.end] == hit.text == "Project\nBlue-Jay"


def test_hits_come_in_reading_order_with_positions():
    text = "Project Atlas is a data center in a reinvestment zone."
    hits = RULES.find(text)
    assert [h.start for h in hits] == sorted(h.start for h in hits)
    assert all(text[h.start : h.end] == h.text for h in hits)


def test_the_strongest_kind():
    assert strongest(RULES.find("light industrial data center")) == "direct_term"
    assert strongest(RULES.find("Project Atlas in a reinvestment zone")) == "project_code_name"
    assert strongest(RULES.find("a reinvestment zone")) == "code_word"
    assert strongest([]) is None


def test_snippet_keeps_the_match_and_marks_what_was_cut():
    text = "one two three four five data center six seven eight nine ten"
    start = text.index("data center")
    out = snippet(text, start, start + len("data center"), margin=12)
    assert out == "… four five data center six seven …"
    assert snippet("data center", 0, 11) == "data center"


def test_snippet_is_one_line():
    text = "the proposed\n\n  data\ncenter   site"
    start = text.index("data")
    assert snippet(text, start, start + 11) == "the proposed data center site"


# --- a government's own computers ----------------------------------------------------------------


def test_words_about_a_governments_own_computers_are_recognized():
    """The owner's review of November 23, 2026: 28 of the 58 sites that reached a reviewer were
    a county or a city buying data center services for itself. These are their wordings."""
    own = [
        "Renewal with Example LLC for data center co-location and network services for the county",
        "Purchase of Data Center Services for the Information Technology Department",
        "Appropriating $850,000 for the planned Data Center Refresh Project",
        "Maintenance and support services for critical data center cooling systems",
        "Next generation data center solution for the Technology Department",
        "Replacement of air conditioning units at the Data Center",
        "The vendor has dedicated servers in two physical data centers in other states",
    ]
    for text in own:
        assert RULES.own_computers(text), text


def test_words_about_land_or_a_project_are_never_taken_for_a_governments_own_computers():
    kept = [
        "Discuss a proposed data center on County Road 12",
        "Tax abatement agreement for a data center, with information technology jobs",
        "Moratorium on data centers and battery energy storage systems",
        "Rezoning for a data center campus with on-site cooling systems",
        "Public hearing on a reinvestment zone for a data center and network services hub",
        "Town hall on the data center near Example",
    ]
    for text in kept:
        assert RULES.own_computers(text) is None, text


def test_an_ordinances_definition_of_a_data_center_is_not_a_governments_own_computers():
    """The owner's decision of November 24, 2026.

    This is a real item, from the definitions of a Michigan township's moratorium ordinance. It
    lists "servers", and it was set aside. A definition of the land use is not a purchase.
    """
    definition = (
        "1. Data Center: A facility used for centralized storage, management, processing, and "
        "transmission of digital information, typically containing computer servers, data "
        "storage systems, telecommunications equipment, power distribution systems, cooling "
        "and ventilation"
    )
    assert RULES.own_computers(definition) is None
    # A purchase that lists servers is set aside as before.
    assert RULES.own_computers("Purchase of servers for the county data center") == "servers"


# --- a term that is not a reason by itself --------------------------------------------------------


def test_special_land_use_is_a_reason_only_beside_another_term():
    """The owner's decision of November 24, 2026.

    "Special land use" is Michigan's ordinary term for a use that needs a hearing. On 56 real
    Michigan agendas it was a reason by itself seven times: a drive-through, a campground, a
    market. None was about a data center.
    """
    assert RULES.stands_alone(["special land use"]) is False
    assert RULES.stands_alone(["special land use", "special land use"]) is False
    assert RULES.stands_alone(["special land use", "data center"]) is True
    assert RULES.stands_alone(["special land use", "light industrial"]) is True
    assert RULES.stands_alone(["special land use", "Project Falcon"]) is True
    # Every other term is a reason by itself, as it was.
    for term in ("data center", "reinvestment zone", "development agreement", "large load"):
        assert RULES.stands_alone([term]) is True
    assert RULES.stands_alone([]) is False


# --- the words of a government writing its own rules ----------------------------------------------


def test_the_words_of_rule_making_are_found_whole_and_in_the_lists_order():
    said = "First reading of a general Moratorium\nOrdinance on data centers, and two ordinances."
    assert RULES.rule_making(said) == ["moratorium", "ordinance"]
    assert RULES.rule_making("Zoning text amendments for the overlay district") == [
        "text amendment"
    ]
    assert RULES.rule_making("A coordinance of moratoria") == []
    assert RULES.rule_making("Presentation on a proposed data center and its water use") == []
