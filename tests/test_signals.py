"""Stored documents become draft signals: the rules, against saved copies of real records.

The TCEQ lists and the Comptroller list are saved copies. The well report extract is made
from the hand-built sample. The planning group files are synthetic, made here.
"""

from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path

import pytest

from collectors.base import LayoutChanged
from collectors.tx import tceq_air_pending_legacy as tceq
from collectors.tx import twdb_well_reports as twdb
from pipeline.config import load_counties
from pipeline.extract import extract
from pipeline.signals import (
    PROCESSORS,
    Doc,
    Rules,
    ercot_rpg_file,
    process,
    read_listings,
    tceq_air_pending,
    twdb_well_reports_extract,
)

from .helpers import make_pdf

FIXTURES = Path(__file__).parent / "fixtures"
LIST = (FIXTURES / "tx_comptroller_data_centers" / "data-center-lists.html").read_bytes()
NSR = (FIXTURES / "tx_tceq_air_pending_legacy" / "nsr-pending-permits.html").read_bytes()
TITLE_V = (FIXTURES / "tx_tceq_air_pending_legacy" / "titlev-pending-permits.html").read_bytes()
WELLS = (FIXTURES / "tx_twdb_well_reports" / "welldata-sample.txt").read_bytes()

NOW = dt.datetime(2026, 11, 20, 12, 0, tzinfo=dt.UTC)
RULES = Rules(listings=read_listings(LIST), listings_sha256=hashlib.sha256(LIST).hexdigest())
NO_LIST = Rules(listings={})


def doc(source_id: str, url: str, body: bytes, text: str = "", meta: dict | None = None) -> Doc:
    return Doc(source_id, url, NOW, hashlib.sha256(body).hexdigest(), text, meta or {}, body)


def tceq_doc(url: str, body: bytes) -> Doc:
    return doc("tx_tceq_air_pending_legacy", url, body)


def well_extract(*rows: str, counties: frozenset[str] | None = None) -> Doc:
    """The stored extract the collector would make from the sample, or from the given rows."""
    if rows:
        body = ("\n".join(["|".join(twdb.KEEP), *rows]) + "\n").encode()
    else:
        names = counties or frozenset(c.name for c in load_counties("TX").counties)
        lines = WELLS.decode(twdb.ENCODING).split("\r\n")
        body = twdb.reduce_table(lines, names, dt.date(2024, 11, 20)).body()
    return doc("tx_twdb_well_reports", twdb.URL, body)


def well_row(**values: str) -> str:
    row = dict.fromkeys(twdb.KEEP, "")
    row.update(
        WellReportTrackingNumber="9100001", DateSubmitted="2026-10-01", County="Hood",
        OwnerName="Example Data Center LLC", ProposedUse="Industrial", TypeOfWork="New Well",
    )  # fmt: skip
    row.update(values)
    return "|".join(row[name] for name in twdb.KEEP)


def rpg_doc(pages: list[str], url: str | None = None) -> Doc:
    body = make_pdf(pages)
    url = url or "https://www.ercot.com/files/docs/2026/07/17/6.-Status-Update_July2026_RPG.pdf"
    return doc("tx_ercot_rpg", url, body, text=extract(body, "application/pdf").text)


# --- the Comptroller list -----------------------------------------------------------------------


def test_the_list_gives_every_company_with_its_role():
    listings = read_listings(LIST)
    assert len(listings) > 200
    found = listings["CYRUSONE LLC"]
    assert {x.role for x in found} <= {"owner", "occupant", "operator"}
    assert all(x.data_center for x in found)


# --- TCEQ lists ---------------------------------------------------------------------------------


def test_a_tceq_row_needs_a_reason():
    out = tceq_air_pending(tceq_doc(tceq.NSR, NSR), RULES)
    assert out.records == 296
    assert out.no_reason == 290 and len(out.drafts) == 6
    assert out.records == out.no_reason + out.held_back + out.undated + len(out.drafts)


def test_a_tceq_signal_restates_the_row_and_says_why():
    out = tceq_air_pending(tceq_doc(tceq.NSR, NSR), RULES)
    by_permit = {d.extracted["row"]["permit_number"]: d for d in out.drafts}
    draft = by_permit["131651"]
    assert draft.signal_type == "air_permit"
    assert draft.event_date == dt.date(2026, 3, 30)
    assert draft.summary == (
        "TCEQ lists a pending New Source Review air permit application from ALIGNED DATA "
        "CENTERS REIT LLC for ADC PLANO: permit 131651, received March 30, 2026."
    )
    assert draft.party == "ALIGNED DATA CENTERS REIT LLC" and draft.party_kind == "company"
    assert draft.county_fips is None  # the lists give no county
    assert draft.confidence == 0.9
    assert draft.extracted["reasons"] == [
        {"rule": "direct_term", "term": "data center", "field": "applicant",
         "text": "DATA CENTERS"}
    ]  # fmt: skip
    assert draft.extracted["row"]["application_url"].startswith("https://www.tceq.texas.gov/")


def test_a_summary_never_says_a_data_center_is_planned():
    for url, body in ((tceq.NSR, NSR), (tceq.TITLE_V, TITLE_V)):
        for draft in tceq_air_pending(tceq_doc(url, body), RULES).drafts:
            assert draft.summary.startswith("TCEQ lists a pending ")
            assert "planned" not in draft.summary.lower()


def test_a_company_on_the_comptroller_list_is_a_weaker_reason_than_the_words():
    out = tceq_air_pending(tceq_doc(tceq.TITLE_V, TITLE_V), RULES)
    by_permit = {d.extracted["row"]["permit_number"]: d for d in out.drafts}
    listed_only = by_permit["4941"]  # CyrusOne LLC, with a site name that says nothing
    assert [r["rule"] for r in listed_only.extracted["reasons"]] == ["listed_company"]
    assert listed_only.confidence == 0.5
    reason = listed_only.extracted["reasons"][0]
    assert reason["list"] == "tx_comptroller_data_centers"
    assert reason["list_sha256"] == hashlib.sha256(LIST).hexdigest()
    assert reason["listed_as"][0]["name"]
    assert by_permit["4262"].confidence == 0.9  # the site is named a data center


def test_without_the_list_only_the_words_count():
    out = tceq_air_pending(tceq_doc(tceq.TITLE_V, TITLE_V), NO_LIST)
    assert len(out.drafts) == 4
    assert all(d.confidence == 0.9 for d in out.drafts)


def test_the_same_application_has_the_same_fingerprint_in_a_later_copy_of_the_list():
    first = tceq_air_pending(tceq_doc(tceq.NSR, NSR), RULES).drafts
    later = tceq_air_pending(tceq_doc(tceq.NSR, NSR + b"<!-- rebuilt -->"), RULES).drafts
    source = "tx_tceq_air_pending_legacy"
    assert [d.fingerprint(source) for d in first] == [d.fingerprint(source) for d in later]
    assert len({d.fingerprint(source) for d in first}) == len(first)


def test_the_two_lists_do_not_share_fingerprints():
    source = "tx_tceq_air_pending_legacy"
    nsr = {d.fingerprint(source) for d in tceq_air_pending(tceq_doc(tceq.NSR, NSR), RULES).drafts}
    title_v = {
        d.fingerprint(source)
        for d in tceq_air_pending(tceq_doc(tceq.TITLE_V, TITLE_V), RULES).drafts
    }
    assert not nsr & title_v


def test_a_tceq_applicant_who_may_be_a_person_makes_no_signal():
    # Give a real data center row an applicant that shows no company.
    body = NSR.replace(b"ALIGNED DATA CENTERS REIT LLC", b"INVENTED PERSON")
    assert body != NSR
    before = tceq_air_pending(tceq_doc(tceq.NSR, NSR), RULES)
    out = tceq_air_pending(tceq_doc(tceq.NSR, body), RULES)
    # The site name alone gave no reason for this row, so it is simply not a signal.
    assert len(out.drafts) == len(before.drafts) - 1
    assert all(d.party != "INVENTED PERSON" for d in out.drafts)

    body = NSR.replace(b"CRUSOE ENERGY SYSTEMS LLC", b"INVENTED PERSON")
    out = tceq_air_pending(tceq_doc(tceq.NSR, body), RULES)
    # These rows still give a reason, the site is named a data center. They are held back.
    assert out.held_back == 2
    assert out.held_refs == [
        "TCEQ New Source Review permit 182126, GHGPSDTX263, PSDTX1688",
        "TCEQ New Source Review permit 182880, GHGPSDTX268, PSDTX1698",
    ]
    assert all("INVENTED" not in ref for ref in out.held_refs)
    assert all(d.party != "INVENTED PERSON" for d in out.drafts)


def test_a_page_that_is_not_one_of_the_lists_is_refused():
    with pytest.raises(LayoutChanged):
        tceq_air_pending(tceq_doc("https://www.tceq.texas.gov/other.html", NSR), RULES)


# --- TWDB well reports --------------------------------------------------------------------------


def test_well_reports_from_the_sample():
    out = twdb_well_reports_extract(well_extract(), RULES)
    # The extract keeps six rows. Three name a data center company in a test county.
    assert out.records == 6
    assert sorted(d.extracted["row"]["WellReportTrackingNumber"] for d in out.drafts) == [
        "728122", "731019", "731020",
    ]  # fmt: skip
    assert out.no_reason == 3 and out.held_back == 0


def test_a_well_signal_restates_the_report():
    out = twdb_well_reports_extract(well_extract(), RULES)
    draft = next(d for d in out.drafts if d.key == "well_report:728122")
    assert draft.signal_type == "well_report"
    assert draft.event_date == dt.date(2026, 7, 16)
    assert draft.county_fips == "48035"  # Bosque
    assert draft.party == "CyrusOne Bosque LLC"
    assert draft.summary == (
        "Texas well report 728122 names CyrusOne Bosque LLC as owner of a well in Bosque "
        "County. Proposed use: Public Supply. Type of work: New Well. Submitted July 16, 2026."
    )
    assert draft.extracted["point"] == {
        "lon": -97.372186, "lat": 31.849363,
        "from": "the well report. Not verified by state staff.",
    }  # fmt: skip
    assert draft.extracted["row"]["DrillingStartDate"] == "2026-04-20"


def test_a_project_company_named_for_a_listed_company_is_a_loose_match():
    # "CyrusOne Bosque LLC" is not on the list. "CyrusOne LLC" is.
    out = twdb_well_reports_extract(well_extract(), RULES)
    draft = next(d for d in out.drafts if d.key == "well_report:728122")
    (reason,) = draft.extracted["reasons"]
    assert reason["rule"] == "listed_company_loose"
    assert reason["match"] == "the name starts with a listed name"
    assert reason["listed_as"][0]["name"].upper().startswith("CYRUSONE")
    assert draft.confidence == 0.3


def test_how_a_name_relates_to_the_list():
    def rule(name: str) -> tuple[str, str] | None:
        found = [r for r in RULES.reasons({}, name) if r["rule"].startswith("listed")]
        return (found[0]["rule"], found[0]["match"]) if found else None

    assert rule("CyrusOne LLC") == ("listed_company", "the same name")
    assert rule("CYRUSONE, L.L.C.") == ("listed_company", "the same name")
    assert rule("CyrusOne Inc") == (
        "listed_company_loose", "the same name with another legal form",
    )  # fmt: skip
    assert rule("CyrusOne Bosque LLC") == (
        "listed_company_loose", "the name starts with a listed name",
    )  # fmt: skip
    assert rule("Bosque CyrusOne LLC") is None
    assert rule("Invented Gas Station LLC") is None


def test_an_ordinary_word_on_the_list_does_not_tie_a_longer_name_to_it():
    assert "DESIGN" in {k for k in RULES.listings if " " not in k} | {"DESIGN"}
    reasons = RULES.reasons({}, "Design Homes LLC")
    assert reasons == []
    reasons = RULES.reasons({}, "Switch Energy Partners LLC")
    assert reasons == []


def test_a_data_center_named_in_a_well_owner_is_a_direct_reason():
    out = twdb_well_reports_extract(well_extract(), RULES)
    draft = next(d for d in out.drafts if d.key == "well_report:731020")
    assert draft.confidence == 0.9
    assert draft.extracted["reasons"][0] == {
        "rule": "direct_term", "term": "data center", "field": "owner", "text": "Data Centers",
    }  # fmt: skip


def test_a_well_owner_who_may_be_a_person_is_held_back_by_number_only():
    rows = [
        well_row(WellReportTrackingNumber="9100002", OwnerName="INVENTED PERSON",
                 Comments="water for the data center next door"),
        well_row(WellReportTrackingNumber="9100003", OwnerName="Invented Family Trust",
                 WellAddress1="1 Data Center Way"),
    ]  # fmt: skip
    out = twdb_well_reports_extract(well_extract(*rows), RULES)
    assert out.drafts == []
    assert out.held_back == 2
    assert out.held_refs == ["TWDB well report 9100002", "TWDB well report 9100003"]


def test_free_text_is_searched_and_never_copied_whole():
    comment = (
        "Invented Driller Name called the owner at 555-0100 about access. Water supply for "
        "data center construction. Gate code is on file with the invented site manager."
    )
    out = twdb_well_reports_extract(
        well_extract(well_row(Comments=comment, WellLocationDescription="north pasture")), RULES
    )
    (draft,) = out.drafts
    assert "Comments" not in draft.extracted["row"]
    assert "WellLocationDescription" not in draft.extracted["row"]
    (piece,) = draft.extracted["free_text_matches"]["Comments"]
    assert "data center" in piece
    # Only the words next to the match are kept, not the names and numbers further off.
    assert "555-0100" not in piece and "Invented Driller Name" not in piece
    assert "invented site manager" not in piece
    assert comment not in str(draft.extracted)


def test_a_well_with_no_reason_or_no_date_or_another_county_makes_no_signal():
    rows = [
        well_row(WellReportTrackingNumber="1", OwnerName="Invented Gas Station LLC"),
        well_row(WellReportTrackingNumber="2", DateSubmitted=""),
        well_row(WellReportTrackingNumber="3", County="Medina"),
    ]
    out = twdb_well_reports_extract(well_extract(*rows), NO_LIST)
    assert out.drafts == []
    assert (out.no_reason, out.undated, out.out_of_scope) == (1, 1, 1)


def test_coordinates_outside_texas_are_not_kept():
    rows = [
        well_row(CoordDDLat="32.44", CoordDDLong="97.79"),  # the minus sign is missing
        well_row(WellReportTrackingNumber="9100009", CoordDDLat="", CoordDDLong=""),
    ]
    out = twdb_well_reports_extract(well_extract(*rows), RULES)
    assert [d.extracted["point"] for d in out.drafts] == [None, None]


def test_an_extract_in_another_shape_is_refused():
    bad = doc("tx_twdb_well_reports", twdb.URL, b"a|b|c\n1|2|3\n")
    with pytest.raises(LayoutChanged):
        twdb_well_reports_extract(bad, RULES)


# --- ERCOT planning group files -----------------------------------------------------------------


def test_a_planning_file_gives_one_signal_per_test_county_named_with_a_term():
    out = ercot_rpg_file(
        rpg_doc(
            [
                "Example Electric Cooperative\nHood County Large Load Project\nStatus update",
                "The project serves a 300 MW large load on a 600-acre site in Hood County.\n"
                "Estimated cost $85 million. Sponsor: Example Transmission Company LLC.",
                "Appendix: line ratings",
            ]
        ),
        RULES,
    )
    (draft,) = out.drafts
    assert draft.signal_type == "transmission_filing"
    assert draft.county_fips == "48221"
    assert draft.event_date == dt.date(2026, 7, 17)  # from the file's address
    assert draft.party is None
    assert draft.summary == (
        'ERCOT Regional Planning Group file "6.-Status-Update_July2026_RPG.pdf", posted '
        'July 17, 2026, mentions "large load" and Hood County.'
    )
    assert draft.confidence == 0.3
    kinds = {(q["kind"], q["value"]) for q in draft.extracted["quantities"]}
    assert kinds == {("megawatts", 300.0), ("acres", 600.0), ("dollars", 85e6)}
    assert draft.extracted["companies_named"] == ["Example Transmission Company LLC"]
    assert any("300 MW large load" in s for s in draft.extracted["snippets"])
    assert out.county_fips == "48221"  # the whole file is about one county


def test_a_file_about_a_county_outside_the_test_set_makes_no_signal():
    out = ercot_rpg_file(
        rpg_doc(["Example Medina County Large Load Project\n250 MW of new load"]), RULES
    )
    assert out.drafts == [] and out.out_of_scope == 1


def test_a_file_naming_two_test_counties_gives_two_signals():
    out = ercot_rpg_file(
        rpg_doc(
            [
                "Large load additions in Hood County: 300 MW",
                "Large load additions in Bosque County: 120 MW",
                "Medina County reliability upgrade",
            ]
        ),
        RULES,
    )
    assert [d.county_fips for d in out.drafts] == ["48035", "48221"]
    assert out.county_fips is None
    hood = out.drafts[1]
    assert [q["value"] for q in hood.extracted["quantities"]] == [300.0]
    assert hood.extracted["other_counties_named"] == ["Medina"]
    assert len({d.fingerprint("tx_ercot_rpg") for d in out.drafts}) == 2


def test_the_wording_of_a_real_planning_file():
    # Two sentences as a real file writes them, with the headings that sit near them.
    out = ercot_rpg_file(
        rpg_doc(
            [
                "Introduction\nExample Energy submitted the Large Load Additions Project "
                "(25RPG020) for review.\nThis is a Tier 1 project with an estimated cost of "
                "approximately $333.7 million.\nThis project is needed to address reliability "
                "in Bexar and Medina counties with the addition of approximately 2 GW Load by "
                "2035.",
                "TPIT Project Name Tier Project ISD County(s)\nProject COD Capacity (~MW) County",
            ]
        ),
        RULES,
    )
    (draft,) = out.drafts
    assert draft.county_fips == "48029"  # Bexar
    assert draft.extracted["other_counties_named"] == ["Medina"]
    assert [r["term"] for r in draft.extracted["reasons"]] == ["large load"]
    found = {(q["kind"], q["value"]) for q in draft.extracted["quantities"]}
    assert found == {("dollars", 333.7e6), ("megawatts", 2000.0)}
    # ERCOT's own number for the project ties next month's update to this one.
    assert draft.extracted["project_numbers"] == ["25RPG020"]


def test_a_project_name_is_not_a_reason_in_a_planning_file():
    out = ercot_rpg_file(rpg_doc(["Project Falcon in Hood County\n138 kV line rebuild"]), RULES)
    assert out.drafts == [] and out.no_reason == 1


def test_a_term_with_no_county_anywhere_gives_a_signal_with_no_county():
    out = ercot_rpg_file(rpg_doc(["Large load interconnection study\n500 MW"]), RULES)
    (draft,) = out.drafts
    assert draft.county_fips is None
    assert draft.summary.endswith('mentions "large load".')
    assert draft.extracted["placement"] == "no single county could be tied to the term"


def test_a_county_named_on_another_page_counts_when_it_is_the_only_one():
    out = ercot_rpg_file(
        rpg_doc(["Hood County transmission project", "Driver: a new data center campus"]), RULES
    )
    (draft,) = out.drafts
    assert draft.county_fips == "48221"
    assert draft.extracted["placement"] == "the only county the file names"
    assert draft.confidence == 0.9


def test_a_file_with_no_term_makes_no_signal():
    out = ercot_rpg_file(rpg_doc(["Hood County line rebuild\n138 kV"]), RULES)
    assert out.drafts == [] and out.no_reason == 1


def test_index_and_meeting_pages_are_not_read_for_signals():
    page = doc(
        "tx_ercot_rpg", "https://www.ercot.com/calendar/11032026-RPG-Meeting", b"<html></html>",
        text="Hood County Large Load Project",
    )  # fmt: skip
    out = ercot_rpg_file(page, RULES)
    assert out.drafts == [] and out.records == 0


def test_a_file_whose_address_carries_no_date_makes_no_signal():
    out = ercot_rpg_file(
        rpg_doc(["Hood County large load"], url="https://www.ercot.com/files/docs/undated.pdf"),
        RULES,
    )
    assert out.drafts == [] and out.undated == 1


# --- all processors -----------------------------------------------------------------------------


def test_every_processor_belongs_to_a_source_that_feeds_signals():
    from pipeline.config import load_sources

    sources = load_sources()
    for source_id in PROCESSORS:
        assert sources.by_id(source_id).layer == "signal"


def test_every_draft_uses_a_signal_type_from_the_scoring_file():
    out = process(tceq_doc(tceq.NSR, NSR), RULES)
    assert {d.signal_type for d in out.drafts} == {"air_permit"}
    assert all(0 < d.confidence <= 1 for d in out.drafts)
