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
