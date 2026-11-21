"""The Texas agenda inventory is complete, and no row claims more than its addresses show."""

from __future__ import annotations

import collections
import re

import pytest
from pydantic import ValidationError

from pipeline import agenda_inventory as inv
from pipeline.config import load_counties

BASE = {
    "government": "Example city",
    "counties": ("Hood",),
    "body": "Example City Council",
    "body_type": "city_council",
    "official_site": "https://www.example-tx.gov/",
    "agenda_url": "https://www.example-tx.gov/AgendaCenter",
    "platform": "civicplus_agendacenter",
    "evidence": "https://www.example-tx.gov/AgendaCenter/ViewFile/Agenda/_11172026-101",
    "status": "seen",
    "notes": "",
}


def body(**changes) -> inv.AgendaBody:
    return inv.AgendaBody(**{**BASE, **changes})


# --- naming a platform from an address ----------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "platform"),
    [
        ("https://www.example-tx.gov/AgendaCenter", "civicplus_agendacenter"),
        ("https://tx-example.civicplus.com/AgendaCenter/City-Council-2", "civicplus_agendacenter"),
        ("https://exampletx.portal.civicclerk.com/", "civicclerk"),
        ("https://example.legistar.com/Calendar.aspx", "legistar"),
        ("https://example.granicus.com/ViewPublisher.php?view_id=1", "granicus"),
        ("https://example-tx.municodemeetings.com/", "municode_meetings"),
        ("https://meetings.municode.com/PublishPage/index?cid=EXAMPLE", "municode_meetings"),
        ("https://go.boarddocs.com/tx/example/Board.nsf/Public", "boarddocs"),
        ("https://example.novusagenda.com/agendapublic/", "novusagenda"),
        ("https://example.primegov.com/public/portal", "primegov"),
        ("https://pub-example.escribemeetings.com/", "escribe"),
        ("https://exampletx.iqm2.com/Citizens/Default.aspx", "iqm2"),
        ("https://example.civicweb.net/Portal/", "civicweb"),
        ("https://exampletx.swagit.com/city-council", "swagit"),
        (
            "https://swagit-attachments.granicus.com/uploads/video/agenda_file/1/a.pdf",
            "swagit",
        ),
        (
            "https://mccmeetings.blob.core.usgovcloudapi.net/exampletx-pubu/MEET-Agenda-0.pdf",
            "municode_meetings",
        ),
        ("https://public.destinyhosted.com/agenda_publish.cfm?id=1", "destiny_hosted"),
    ],
)
def test_an_outside_platform_is_named_from_its_address(url, platform):
    assert inv.platform_of(url) == platform


@pytest.mark.parametrize(
    "url",
    [
        "",
        "https://www.example-tx.gov/agendas",
        "https://www.co.hood.tx.us/page/hood.Agendas",
        # A word in a path or a look-alike host names nothing.
        "https://www.example-tx.gov/legistar-archive.pdf",
        "https://www.example-tx.gov/files/agendacenter-notes.pdf",
        "https://notcivicclerk.example.org/",
    ],
)
def test_an_address_that_names_no_platform_says_nothing(url):
    assert inv.platform_of(url) is None


def test_a_county_association_site_is_recognized_by_its_host():
    assert inv.is_county_site("https://www.co.hood.tx.us/page/hood.Agendas")
    assert inv.is_county_site("http://co.san-saba.tx.us/page/sansaba.Agendas")
    assert not inv.is_county_site("https://www.hoodcounty.texas.gov/agendas")
    assert not inv.is_county_site("")


# --- what a row may claim -----------------------------------------------------------------------


def test_a_row_whose_addresses_show_its_platform_is_accepted():
    assert body().platform == "civicplus_agendacenter"
    # The agenda page can be on the city's site while the files sit on the platform.
    assert body(
        agenda_url="https://www.example-tx.gov/meetings",
        platform="legistar",
        evidence="https://example.legistar.com/Calendar.aspx",
    )


def test_a_platform_no_address_on_the_row_shows_is_refused():
    with pytest.raises(ValidationError, match="no address on the row shows legistar"):
        body(platform="legistar")
    with pytest.raises(ValidationError, match="no address on the row shows civicclerk"):
        body(
            agenda_url="https://www.example-tx.gov/agendas",
            platform="civicclerk",
            evidence="the page looks like CivicClerk",
        )


def test_own_site_files_cannot_sit_on_an_outside_platform():
    assert body(
        agenda_url="https://www.example-tx.gov/agendas",
        platform="own_site_files",
        evidence="https://www.example-tx.gov/files/agenda-2026-11-17.pdf",
    )
    with pytest.raises(ValidationError, match="is a civicplus_agendacenter address"):
        body(platform="own_site_files")


def test_a_county_association_row_needs_that_kind_of_address():
    row = {
        "government": "Hood County",
        "body": "Hood County Commissioners Court",
        "body_type": "commissioners_court",
        "platform": "cira_county_site",
        "evidence": "",
    }
    assert body(**row, agenda_url="https://www.co.hood.tx.us/page/hood.Agendas")
    with pytest.raises(ValidationError, match="needs a co.<name>.tx.us"):
        body(**row, agenda_url="https://www.hoodcounty.texas.gov/agendas")


def test_nothing_found_is_recorded_as_not_found_and_claims_no_page():
    assert body(
        official_site="",
        agenda_url="",
        platform="no_website",
        evidence="",
        status="not_found",
        notes="Facebook page only",
    )
    with pytest.raises(ValidationError, match="no_website with an address"):
        body(platform="no_website", evidence="", status="not_found")
    with pytest.raises(ValidationError, match="must have status not_found"):
        body(agenda_url="", platform="none_online", evidence="", status="seen")
    with pytest.raises(ValidationError, match="with no agenda address"):
        body(agenda_url="")
    with pytest.raises(ValidationError, match="with status not_found"):
        body(status="not_found")


def test_not_determined_and_other_must_say_why():
    with pytest.raises(ValidationError, match="needs a note"):
        body(agenda_url="", platform="not_determined", evidence="", status="not_found", notes=" ")
    with pytest.raises(ValidationError, match="needs a note"):
        body(agenda_url="https://www.example-tx.gov/agendas", platform="other", evidence="x")


def test_an_address_must_be_a_web_address():
    with pytest.raises(ValidationError):
        body(official_site="www.example-tx.gov")
    with pytest.raises(ValidationError):
        body(agenda_url="see the city website")


# --- the inventory file -------------------------------------------------------------------------


@pytest.fixture(scope="module")
def bodies() -> list[inv.AgendaBody]:
    return inv.load_inventory()


def test_the_place_list_holds_every_incorporated_place_once():
    places = inv.load_places()
    assert len(places) == 304
    assert len({name for name, _ in places}) == 304
    scope = {c.name for c in load_counties("TX").counties}
    assert {c for _, counties in places for c in counties} == scope


def test_every_county_has_its_commissioners_court(bodies):
    courts = collections.Counter(
        b.government for b in bodies if b.body_type == "commissioners_court"
    )
    expected = {f"{c.name} County" for c in load_counties("TX").counties}
    assert set(courts) == expected
    assert set(courts.values()) == {1}


def test_every_incorporated_place_has_its_council(bodies):
    councils = collections.Counter(b.government for b in bodies if b.body_type == "city_council")
    places = dict(inv.load_places())
    assert set(councils) == set(places)
    assert set(councils.values()) == {1}
    for b in bodies:
        if b.government in places:
            assert b.counties == places[b.government], b.body


def test_every_body_belongs_to_a_government_in_the_inventory(bodies):
    governments = {
        b.government for b in bodies if b.body_type in ("commissioners_court", "city_council")
    }
    assert {b.government for b in bodies} == governments
    assert len({(b.government, b.body) for b in bodies}) == len(bodies)


_TITLE_THEN_NAME = re.compile(
    r"\b(?:Mayor|Judge|Clerk|Secretary|Commissioner|Councilmember|Councilman|Councilwoman|"
    r"Alderman|Chairman|Chairwoman|Director|Manager)\s+(?!Pro\b|Precinct\b|Court|Position\b|Place\b)"
    r"[A-Z][a-z]+"
)


def test_no_row_names_a_person(bodies):
    """Bodies and addresses only: no official's name and no email address."""
    for b in bodies:
        assert not _TITLE_THEN_NAME.search(b.notes), (b.body, b.notes)
        assert "@" not in f"{b.notes} {b.evidence} {b.agenda_url}", b.body


# --- what each platform's own rules say ---------------------------------------------------------


def test_every_platform_has_its_standing_on_file():
    terms = inv.load_platform_terms()
    assert set(terms) == set(inv.FOUND)


def test_the_platforms_whose_rules_bar_a_collector_are_marked_so():
    """Read on November 21, 2026. Changing one of these takes a new reading and the owner's word."""
    terms = inv.load_platform_terms()
    standing = {name: t.status for name, t in terms.items() if t.status != "not_read"}
    assert standing == {
        "civicplus_agendacenter": "restricted",
        "civicclerk": "restricted",
        "municode_meetings": "restricted",
        "granicus": "restricted",
        "civicweb": "restricted",
        "swagit": "restricted",
        "legistar": "cleared",
        "cira_county_site": "candidate",
        "own_site_files": "cleared",
    }
    # Both were cleared on the owner's word, after their rules and each government's were read.
    # Own sites have no vendor: each site's own robots file and terms decide.
    cleared = sorted(name for name, t in terms.items() if t.status == "cleared")
    assert cleared == ["legistar", "own_site_files"]


def test_a_platform_cannot_be_cleared_against_its_robots_file_or_without_a_date():
    base = {
        "platform": "legistar",
        "vendor": "Example vendor",
        "robots": "none",
        "checked_on": "2026-11-21",
        "terms_url": "",
        "note": "Made up for a test.",
    }
    assert inv.PlatformTerms(**base, status="cleared")
    with pytest.raises(ValidationError, match="robots file that does not allow it"):
        inv.PlatformTerms(**{**base, "robots": "disallowed"}, status="cleared")
    with pytest.raises(ValidationError, match="needs the date read"):
        inv.PlatformTerms(**{**base, "checked_on": ""}, status="candidate")
    with pytest.raises(ValidationError, match="not a platform"):
        inv.PlatformTerms(**{**base, "platform": "no_website"}, status="not_read")


def test_each_sites_own_terms_are_on_file_once_and_for_a_government_we_know():
    rows = inv.load_site_terms()
    hosts = [r["host"] for r in rows]
    # 38 Agenda Center sites, 14 on Legistar and 76 that post files on their own site
    assert len(set(hosts)) == len(hosts) == 128
    governments = {b.government for b in inv.load_inventory()}
    results = {
        "own_pages_silent", "links_vendor_terms", "no_terms_found", "could_not_read",
        "reuse_needs_consent", "bars_automated_access", "robots_bar", "refused",
    }  # fmt: skip
    for r in rows:
        assert r["government"] in governments, r["host"]
        assert r["result"] in results, r["host"]
        assert r["platform"] in inv.FOUND
