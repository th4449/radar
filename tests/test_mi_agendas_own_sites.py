"""The own-sites agenda collector for Michigan, run against saved pages.

Ten real pages, saved on November 23, 2026 with one identified request each and cut down to the
part that lists agendas. Each fixture's .meta.json says so. Every one was a page the agenda
inventory cleared that day, of a governing body, and between them they cover the six counties.
Chelsea's was closed later the same day. No test here touches the network.

The source is marked manual: no job reads it until the owner says so. The run tests use a copy
of the source marked http, as it will be then.
"""

from __future__ import annotations

import collections
import datetime as dt
import json
from pathlib import Path

import httpx
import pytest

from collectors import run as runner
from collectors.base import Fetcher, LocalArchive, NotPermitted
from collectors.mi.agenda_pages import MichiganAgendaPages
from collectors.tx.agenda_pages import (
    AgendaPages,
    Page,
    cleared_pages,
    find_agenda_links,
    find_date,
    find_meeting_links,
    page_text,
)
from pipeline.config import load_sources
from pipeline.store import MemorySink

from .helpers import CONTACT, FakeClock, Site, make_pdf

FIXTURES = Path(__file__).parent / "fixtures" / "mi_agendas_own_sites"
TODAY = dt.date(2026, 11, 23)
NAMES = (
    "allegan", "auburn-hills", "chelsea", "comstock", "erie", "heath", "luna-pier", "lyndon",
    "novi", "oshtemo", "otsego", "river-rouge", "superior",
)  # fmt: skip
# One page for a single meeting, on four of the sites above. Saved on November 24, 2026.
MEETING_PAGES = ("heath-meeting", "lyndon-meeting", "novi-meeting", "otsego-meeting")
CLEARED = {p.url: p for p in cleared_pages(TODAY, state="MI")}


def meta(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.meta.json").read_text())


def saved(name: str) -> tuple[bytes, str]:
    return (FIXTURES / f"{name}.html").read_bytes(), meta(name)["final_url"]


def links(name: str):
    body, url = saved(name)
    return find_agenda_links(body, url, TODAY)


def days(name: str) -> list[str]:
    return [link.date.isoformat() for link in links(name)]


def source():
    return load_sources().by_id("mi_agendas_own_sites")


def cleared_to_run():
    """The source as it will be once the owner says to run it."""
    return source().model_copy(update={"method": "http"})


# --- the saved pages ----------------------------------------------------------------------------


def test_each_saved_page_is_one_the_inventory_clears_and_was_cut_down():
    assert sorted(p.name.removesuffix(".meta.json") for p in FIXTURES.glob("*.meta.json")) == (
        sorted(NAMES + MEETING_PAGES)
    )
    hosts = {httpx.URL(url).host for url in CLEARED}
    for name in MEETING_PAGES:
        m = meta(name)
        assert m["trimmed"] is True and httpx.URL(m["url"]).host in hosts
    counties = set()
    for name in NAMES:
        m = meta(name)
        assert m["source_id"] == "mi_agendas_own_sites"
        assert m["trimmed"] is True and m["bytes"] < m["original_bytes"]
        assert m["url"] == m["final_url"]  # none of them redirected
        if name == "chelsea":
            # Cleared when it was saved. Closed the same day: its files sit on a host whose
            # robots rule bars them, and the owner said to leave them closed.
            assert m["url"] not in CLEARED
            continue
        page = CLEARED[m["url"]]
        assert len(page.bodies) == 1
        counties.update(page.counties)
    assert counties == {"Allegan", "Kalamazoo", "Monroe", "Oakland", "Washtenaw", "Wayne"}


# --- finding the agendas on a page --------------------------------------------------------------


def test_a_page_revize_builds_gives_each_meetings_agenda_and_leaves_its_packet_and_minutes():
    found = links("chelsea")
    assert days("chelsea") == [
        "2026-11-09", "2026-10-19", "2026-09-28", "2026-09-14", "2026-08-24", "2026-08-10",
    ]  # fmt: skip
    assert {(link.text, link.date_from) for link in found} == {("Agenda", "file_name")}
    # A space in a file's name is written %20. The site's own mark of when a file changed stays.
    assert found[0].url == "https://www.city-chelsea.org/11.09.26%20Agenda.pdf?t=202611051031130"
    body, _ = saved("chelsea")
    assert body.count(b">Packet<") == 6 and body.count(b">Minutes<") == 5


def test_a_link_with_no_host_is_joined_to_the_base_address_the_page_names():
    """The page says in its head what its links are written against, and it is not the page's
    own folder. Joined to the folder, each of Allegan's files was a 404 on two runs by hand."""
    found = links("allegan")
    assert days("allegan")[:2] == ["2026-11-23", "2026-11-09"]
    assert len(found) == 6
    body, url = saved("allegan")
    assert url.endswith("/government/city_council/agendas___minutes.php")
    assert b'<base href="https://www.cityofallegan.org/"' in body
    assert found[0].url == (
        "https://www.cityofallegan.org/11-23-26%20Regular%20Meeting%20Agenda.pdf?t=202611191806150"
    )
    # A file's name can start with something else: "4A 11-09-26 Regular Meeting Agenda.pdf".
    assert found[1].url.startswith("https://www.cityofallegan.org/4A%2011-09-26%20Regular")


def test_a_page_with_no_base_address_joins_its_links_to_its_own_folder():
    page = (
        "<html><head><title>Agendas</title></head><body>"
        '<p><a href="files/11-17-2026 Agenda.pdf">Agenda</a></p></body></html>'
    )
    (link,) = find_agenda_links(
        page.encode(), "https://www.example-twp.org/board/agendas.php", TODAY
    )
    assert link.url == "https://www.example-twp.org/board/files/11-17-2026%20Agenda.pdf"


def test_a_packet_is_taken_where_the_page_posts_nothing_else():
    found = links("comstock")
    assert [(link.text, link.date_from) for link in found][:2] == [
        ("11/16/2026 – Agenda Packet", "link_text"),
        ("10/19/2026 – Agenda Packet", "link_text"),
    ]
    assert days("comstock") == [
        "2026-11-16", "2026-10-19", "2026-10-05", "2026-09-21", "2026-08-19",
    ]  # fmt: skip
    # Two files are named by a string of letters and digits. The link's own words date them.
    assert sum("005056a89546" in link.url for link in found) == 2


def test_a_dated_file_on_a_page_about_meetings_is_an_agenda_though_nothing_says_the_word():
    found = links("erie")
    assert len(found) == 16 and not [link for link in found if "agenda" in link.url.lower()]
    assert days("erie")[-2:] == ["2026-11-12", "2026-11-17"]  # the page runs oldest first
    assert found[-1].text == "November 17, 2026 Regular meeting"
    # A meeting to come is on the page with no file yet. It is not a link.
    body, _ = saved("erie")
    assert b"December 8, 2026" in body and "2026-12-08" not in days("erie")


def test_the_agendas_column_is_taken_and_the_minutes_column_is_left():
    found = links("river-rouge")
    assert days("river-rouge") == [
        "2026-11-17", "2026-11-12", "2026-11-04", "2026-10-20", "2026-10-06", "2026-09-15",
        "2026-09-01",
    ]  # fmt: skip
    assert all("/assets/agenda/agenda" in link.url for link in found)
    body, _ = saved("river-rouge")
    assert body.count(b".pdf") == 14  # the same seven days again, as minutes


def test_a_files_name_dates_its_meeting_where_the_row_gives_the_day_it_was_posted():
    found = links("auburn-hills")
    assert found[0].text == "Meeting Agenda (177 Kb)"
    assert (found[0].date, found[0].date_from) == (dt.date(2026, 11, 23), "file_name")
    body, _ = saved("auburn-hills")
    assert b"11-19-2026" in body  # the day the row says the files were posted
    assert len(found) == 6 and not [link for link in found if "packet" in link.text.lower()]


def test_a_report_of_receipts_and_disbursements_is_not_an_agenda():
    # The page lists the report between the packets, in a file named for the meeting's day.
    # Read as an agenda, it took the place of that day's packet.
    found = links("oshtemo")
    assert days("oshtemo") == [
        "2026-11-24", "2026-11-10", "2026-10-27", "2026-10-13", "2026-09-29", "2026-09-23",
        "2026-09-22", "2026-09-15", "2026-09-09",
    ]  # fmt: skip
    assert not [link for link in found if "rd-report" in link.url]
    assert not [link for link in found if "minutes" in link.text.lower()]
    body, _ = saved("oshtemo")
    assert body.count(b"rd-report.pdf") >= 2


def test_a_notice_that_a_meeting_is_cancelled_is_left():
    found = links("luna-pier")
    assert days("luna-pier")[-2:] == ["2026-10-22", "2026-11-12"]
    assert len(found) == 7
    body, _ = saved("luna-pier")
    assert body.count(b"Canceled") == 2 and "2026-11-26" not in days("luna-pier")


def test_two_meetings_on_one_day_are_both_taken():
    found = links("superior")
    assert len(found) == 14
    by_day = collections.Counter(days("superior"))
    assert by_day["2026-05-18"] == by_day["2026-06-15"] == by_day["2026-10-19"] == 2
    assert found[-1].url.endswith("/2026/11/11.-November-16-2026-Regular-Meeting-Agenda.pdf")


def test_a_page_that_leads_to_a_page_for_each_meeting_gives_no_file():
    """Novi's list links each agenda to a page of its own, so the list holds no file.

    The collector then follows the list to each meeting's page. See the tests of that below.
    """
    body, url = saved("novi")
    assert body.count(b'href="/agendas-minutes/city-council/2026/') == 6
    assert links("novi") == []


# --- dates, as Michigan sites write them --------------------------------------------------------
#
# Every name and address below is one a cleared page gave on the run by hand of November 23,
# 2026. Each was read wrongly, or not at all, before that run.


@pytest.mark.parametrize(
    ("name", "day"),
    [
        # The day run onto the year. Read before as October 20.
        ("August-102026-PC-Pack.pdf", dt.date(2026, 8, 10)),
        # The month run onto the word before it, the day onto the year. Read before as July 20.
        ("Council_PacketAPR72026.pdf", dt.date(2026, 4, 7)),
        # A number before the date. Read before as January 3 of 2027.
        ("1_3-27-2024 PC Agenda.pdf", dt.date(2024, 3, 27)),
        # The day first. Not read before.
        ("GANGES-TOWNSHIP-BOARD-Regular-Monthly-Mtg-Agenda-10Nov2026.pdf", dt.date(2026, 11, 10)),
        ("PC_Agenda_16Nov2026.pdf", dt.date(2026, 11, 16)),
        # And these read as they did.
        ("Agenda-11-9-26-1.pdf", dt.date(2026, 11, 9)),
        ("Council_PacketJuly07072026.pdf", dt.date(2026, 7, 7)),
        ("10.5.26PCMEETINGPACK.pdf", dt.date(2026, 10, 5)),
        ("CA112426.pdf", dt.date(2026, 11, 24)),
    ],
)
def test_a_date_in_a_michigan_files_name_is_read(name, day):
    assert find_date(name, TODAY, runs=True) == day


def listed(href: str, text: str = "Agenda"):
    page = (
        "<html><head><title>Agendas and Minutes</title></head><body>"
        f'<table><tr><td><a href="{href}">{text}</a></td></tr></table></body></html>'
    )
    return find_agenda_links(page.encode(), "https://www.example-twp.org/agendas.php", TODAY)


def test_digits_run_together_are_not_a_date_when_the_files_year_folder_says_otherwise():
    # A document center files by year. a120626 in the folder for 2012 is December 26 of 2012.
    # It was read as December 6 of 2026, and so as the newest agenda on the page.
    old = listed("/document_center/Agendas & Minutes/Township Board/2012/Agendas/a120626s.pdf")
    assert [link.date for link in old] == [None]
    new = listed("/document_center/Agendas & Minutes/Township Board/2026/Agendas/a112426.pdf")
    assert [link.date for link in new] == [dt.date(2026, 11, 24)]
    # A date written out is not second-guessed: one site keeps its 2026 files in a 2024 folder.
    kept = listed("/Agendas & Minutes/Planning Commission/2024/Packets/10-14-26 PC Agenda.pdf")
    assert [link.date for link in kept] == [dt.date(2026, 10, 14)]


def test_a_files_name_cannot_date_a_meeting_long_after_the_file_was_uploaded():
    # A slip of the hand: a packet for January 27, 2026, named 2027, in the folder of the month
    # it was uploaded. It was read as a meeting to come in 2027.
    slip = listed("/wp-content/uploads/2026/01/1.27.2027PCagenda.pdf")
    assert [link.date for link in slip] == [None]
    # An agenda posted the month before its meeting is as it was.
    early = listed("/wp-content/uploads/2026/11/12.08.2026-Agenda.pdf")
    assert [link.date for link in early] == [dt.date(2026, 12, 8)]


def test_a_notice_that_there_is_no_meeting_is_not_an_agenda():
    assert listed("/11.20.2026_SS_No Meeting Notice.pdf", "11.23.2026_SS_No Meeting Notice") == []
    assert len(listed("/11.16.2026 Agenda Packet_FINAL.pdf", "11.16.2026_RM_Agenda Packet")) == 1


# --- which pages --------------------------------------------------------------------------------


def test_the_pages_read_are_the_ones_michigans_inventory_clears():
    governments = {p.government for p in CLEARED.values()}
    # 145 pages of 76 governments until the run by hand of November 23, 2026. It met 24 sites
    # whose agenda files sit on a host that bars them as the sites write their addresses.
    assert (len(CLEARED), len(governments)) == (101, 52)
    assert {"Allegan city", "Novi city", "Oshtemo charter township"} <= governments
    assert not governments & {"Chelsea city", "Pontiac city", "Allen Park city", "Milan city"}
    # Held for the owner by their own terms, built by CivicPlus, refused, or closed by robots.
    assert not governments & {
        "Dearborn city",
        "Keego Harbor city",
        "Rochester city",
        "Detroit city",
        "Dexter township",
        "Rochester Hills city",
    }
    # Ann Arbor's agendas are on Legistar. Its own site is not read for them.
    assert "Ann Arbor city" not in governments
    assert all(p.url.startswith("https://") and p.bodies for p in CLEARED.values())


def test_the_michigan_collector_reads_michigans_inventory_and_the_texas_one_reads_texas():
    michigan = MichiganAgendaPages(today=TODAY)
    assert set(michigan.pages) == set(CLEARED)
    texas = AgendaPages(today=TODAY)
    assert not set(texas.pages) & set(CLEARED)
    assert (michigan.source_id, texas.source_id) == (
        "mi_agendas_own_sites",
        "tx_agendas_own_sites",
    )


# --- a run --------------------------------------------------------------------------------------

COMSTOCK_BODY, COMSTOCK = saved("comstock")
ERIE_BODY, ERIE = saved("erie")
NOVI_BODY, NOVI = saved("novi")
CHELSEA_BODY, CHELSEA = saved("chelsea")
# A made-up page that lists no agenda and leads to none.
EMPTY = "https://www.example-twp.org/agendas"
EMPTY_BODY = b"<html><head><title>Agendas</title></head><body><p>Moved.</p></body></html>"
EMPTY_PAGE = Page(EMPTY, "Example township", ("Washtenaw",), ("Example Township Board",))
PAGES = (CLEARED[COMSTOCK], CLEARED[ERIE], EMPTY_PAGE)
COMSTOCK_FILES = [
    "https://comstockmi.gov/wp-content/uploads/2026/11/Board_Meeting_Agenda-11.16.26.pdf"
]
ERIE_FILES = [
    "https://erietownshipmi.gov/wp-content/uploads/2026/11/November-17-2026-Regular-Meeting-1.pdf",
    "https://erietownshipmi.gov/wp-content/uploads/2026/11/November-12-2026-special-meeting.pdf",
]
PDF = {"Content-Type": "application/pdf"}


def agenda(n: int = 0) -> bytes:
    """A made-up agenda. Each file differs, as real ones do."""
    return make_pdf(["AGENDA", f"Item {n + 1}. Consider a rezoning request."])


def web() -> Site:
    html = {"Content-Type": "text/html; charset=utf-8"}
    routes = {
        COMSTOCK: httpx.Response(200, content=COMSTOCK_BODY, headers=html),
        ERIE: httpx.Response(200, content=ERIE_BODY, headers=html),
        EMPTY: httpx.Response(200, content=EMPTY_BODY, headers=html),
    }
    for n, url in enumerate(COMSTOCK_FILES + ERIE_FILES):
        routes[url] = httpx.Response(200, content=agenda(n), headers=PDF)
    return Site(routes)


def run(site: Site, sink: MemorySink, tmp_path, pages=PAGES):
    clock = FakeClock()
    collector = MichiganAgendaPages(pages=pages, today=TODAY)
    with Fetcher(
        cleared_to_run(), contact=CONTACT, transport=site.transport, clock=clock, sleep=clock.sleep
    ) as fetcher:
        return collector.run(
            source=cleared_to_run(), fetcher=fetcher, store=LocalArchive(tmp_path), sink=sink
        )


def test_a_run_reads_each_page_then_its_recent_agenda_files(tmp_path):
    site, sink = web(), MemorySink()
    summary = run(site, sink, tmp_path)
    assert summary.status == "ok", summary.error
    # The three pages first, then the files from the last three weeks, newest first.
    assert site.page_urls() == [COMSTOCK, ERIE, EMPTY, *COMSTOCK_FILES, *ERIE_FILES]
    assert (summary.documents_seen, summary.documents_new) == (6, 6)
    assert all(r.headers["user-agent"].startswith("DataCenterRadar/") for r in site.requests)
    assert {d.source_id for d in sink.documents.values()} == {"mi_agendas_own_sites"}


def test_a_page_that_gives_no_file_is_named_in_the_run_log(tmp_path):
    sink = MemorySink()
    run(web(), sink, tmp_path)
    assert sink.runs[1]["detail"] == {"governments": 3, "pages_with_no_agenda_links": [EMPTY]}


def test_a_file_is_stored_with_its_government_its_county_and_its_meetings_day(tmp_path):
    sink = MemorySink()
    run(web(), sink, tmp_path)
    docs = {d.url: d for d in sink.documents.values()}
    listing = json.loads(LocalArchive(tmp_path).get(docs[COMSTOCK].storage_path))
    assert listing["government"] == "Comstock charter township" and len(listing["agendas"]) == 5
    file = docs[ERIE_FILES[0]]
    assert "rezoning" in file.text
    kept = {k: file.raw_meta[k] for k in ("record", "government", "counties", "bodies", "page")}
    assert kept == {
        "record": "agenda_file",
        "government": "Erie township",
        "counties": ["Monroe"],
        "bodies": ["Erie Township Board"],
        "page": ERIE,
    }
    assert (file.raw_meta["meeting_date"], file.raw_meta["date_from"]) == (
        "2026-11-17",
        "link_text",
    )


def test_a_second_run_asks_only_for_the_pages(tmp_path):
    sink = MemorySink()
    run(web(), sink, tmp_path)
    again = web()
    summary = run(again, sink, tmp_path)
    assert again.page_urls() == [COMSTOCK, ERIE, EMPTY]
    assert (summary.status, summary.documents_new) == ("ok", 0)


# What Revize's file hosts publish, as read on November 23, 2026. The five named crawlers above
# this rule in the real file are left out.
REVIZE_ROBOTS = """User-agent: *
Allow: /*.pdf$
Allow: /*.DOC$
Allow: /*.DOCX$
Allow: /*.PPT$
Allow: /*.PPTX$
Disallow: /
"""


def test_a_revize_sites_list_is_read_and_its_files_are_refused_as_the_site_writes_them(tmp_path):
    """The run by hand of November 23, 2026 met this on 24 sites.

    A Revize site sends a request for a file on to Revize's file host. That host's robots rule
    allows an address that ends in .pdf. The site writes the address with ?t= and a number
    after it, so the rule bars it. The fetcher obeys the rule as written and leaves the site.
    The owner said to leave those files closed, and the 24 sites are no longer cleared, so no
    run asks. This holds what the fetcher does if one is asked.
    """
    file = "https://www.city-chelsea.org/11.09.26%20Agenda.pdf?t=202611051031130"
    kept_at = "https://cms3.revize.com/revize/chelseami/11.09.26%20Agenda.pdf?t=202611051031130"
    site = web()
    site.routes[CHELSEA] = httpx.Response(200, content=CHELSEA_BODY)
    site.routes[file] = httpx.Response(302, headers={"Location": kept_at})
    site.routes[kept_at] = httpx.Response(200, content=agenda(9), headers=PDF)
    site.routes["https://cms3.revize.com/robots.txt"] = httpx.Response(200, text=REVIZE_ROBOTS)
    sink = MemorySink()
    chelsea = Page(CHELSEA, "Chelsea city", ("Washtenaw",), ("Chelsea City Council",))
    summary = run(site, sink, tmp_path, pages=(chelsea, CLEARED[ERIE]))
    assert summary.status == "partial"
    assert kept_at not in site.page_urls()
    assert list(sink.runs[1]["detail"]["refused_hosts"]) == ["www.city-chelsea.org"]
    assert (
        "robots.txt does not allow"
        in sink.runs[1]["detail"]["refused_hosts"]["www.city-chelsea.org"]
    )
    # The list is still read and stored, and the other site's files are fetched.
    assert {d.url for d in sink.documents.values()} == {CHELSEA, ERIE, *ERIE_FILES}


# --- a list that leads to a page for each meeting -----------------------------------------------
#
# Four sites, four shapes, each saved from the real site. Novi writes the agenda on the meeting's
# page. Heath Township's page links the agenda file on its own site. Otsego's links a file on
# another host. Lyndon Township's links download addresses with no file type.

HTML = {"Content-Type": "text/html; charset=utf-8"}
HEATH_BODY, HEATH = saved("heath")
OTSEGO_BODY, OTSEGO = saved("otsego")
LYNDON_BODY, LYNDON = saved("lyndon")
NOVI_MEETING_BODY, NOVI_MEETING = saved("novi-meeting")
HEATH_MEETING_BODY, HEATH_MEETING = saved("heath-meeting")
OTSEGO_MEETING_BODY, OTSEGO_MEETING = saved("otsego-meeting")
LYNDON_MEETING_BODY, LYNDON_MEETING = saved("lyndon-meeting")
NOVI_COMING = "https://www.cityofnovi.org/agendas-minutes/city-council/2026/nov-23-2026/"
COMING_BODY = (
    b"<html><head><title>Nov 23, 2026</title></head><body><main>Coming Soon</main></body></html>"
)
HEATH_FILE = (
    "https://heathtownship.net/wp-content/uploads/2026/11/"
    "twp-Agenda-Updated-for-November-2026-meeting-1.pdf"
)
OTSEGO_FILE = (
    "https://cdn-www-cityofotsego-org-g4w4.b-cdn.net/wp-content/uploads/2026/11/2.0-AGENDA.pdf"
)


def meetings(name: str):
    body, url = saved(name)
    return find_meeting_links(body, url, TODAY)


def test_a_list_that_links_no_file_gives_the_page_of_each_meeting_and_its_day():
    found = meetings("novi")
    assert [m.url.removeprefix(NOVI) for m in found] == [
        "nov-23-2026/", "nov-9-2026/", "oct-26-2026/", "oct-12-2026/", "sep-28-2026/",
        "sep-14-2026/",
    ]  # fmt: skip
    # The link says "Agenda". The day is in its address.
    assert {(m.text, m.date_from) for m in found} == {("Agenda", "address")}
    assert found[1].date == dt.date(2026, 11, 9)
    # The minutes on the same list are files, and are left.
    assert not [m for m in found if m.url.endswith(".pdf")]


def test_a_meetings_page_is_told_by_its_words_and_its_day_and_other_posts_are_left():
    (only,) = meetings("heath")
    assert (only.url, only.date, only.date_from) == (
        HEATH_MEETING,
        dt.date(2026, 11, 9),
        "link_text",
    )
    # The same post is linked twice, and posts about voting hours are not meetings.
    body, _ = saved("heath")
    assert body.count(b"november-9-2026-township-board-meeting") == 2
    assert body.count(b"early-voting-hours") == 2


def test_a_list_of_document_pages_and_a_list_of_posts_read_the_same_way():
    otsego = meetings("otsego")
    assert len(otsego) == 8 and otsego[0].url == OTSEGO_MEETING
    assert [m.date.isoformat() for m in otsego][:2] == ["2026-11-16", "2026-11-02"]
    # Four posts. The one for the zoning board of appeals says neither agenda nor meeting.
    lyndon = meetings("lyndon")
    assert [m.date.isoformat() for m in lyndon] == ["2026-11-18", "2026-11-10", "2026-11-09"]
    assert lyndon[1].url == LYNDON_MEETING


def test_the_words_of_a_page_are_its_main_part_without_the_sites_menus():
    text = page_text(NOVI_MEETING_BODY)
    assert text.startswith("CITY COUNCIL AGENDA")
    assert "MATTERS FOR COUNCIL ACTION" in text and text.rstrip().endswith("accommodations.")
    assert "\n\n" not in text
    assert page_text(OTSEGO_MEETING_BODY) == "Download"
    # The labels of a page's buttons are not its words. Novi's real page has three above the
    # agenda, and the run by hand of November 24 kept them.
    held = b"<html><body><main><button>ClipNotes</button><p>CITY COUNCIL AGENDA</p></main></body>"
    assert page_text(held) == "CITY COUNCIL AGENDA"


def meeting_web(**more) -> Site:
    routes = {
        NOVI: httpx.Response(200, content=NOVI_BODY, headers=HTML),
        NOVI_COMING: httpx.Response(200, content=COMING_BODY, headers=HTML),
        NOVI_MEETING: httpx.Response(200, content=NOVI_MEETING_BODY, headers=HTML),
        HEATH: httpx.Response(200, content=HEATH_BODY, headers=HTML),
        HEATH_MEETING: httpx.Response(200, content=HEATH_MEETING_BODY, headers=HTML),
        HEATH_FILE: httpx.Response(200, content=agenda(7), headers=PDF),
    }
    routes.update(more)
    return Site(routes)


def test_novis_agenda_is_the_meetings_page_itself_and_no_packet_item_is_asked_for(tmp_path):
    site, sink = meeting_web(), MemorySink()
    summary = run(site, sink, tmp_path, pages=(CLEARED[NOVI],))
    assert summary.status == "ok", summary.error
    # The list, then the two meetings of the last three weeks, newest first. Nothing else.
    assert site.page_urls() == [NOVI, NOVI_COMING, NOVI_MEETING]
    assert not [u for u in site.page_urls() if "/media/" in u]
    doc = next(d for d in sink.documents.values() if d.url == NOVI_MEETING)
    assert doc.text.startswith("CITY COUNCIL AGENDA")
    kept = {k: doc.raw_meta[k] for k in ("record", "government", "counties", "page", "agenda_is")}
    assert kept == {
        "record": "agenda_file",
        "government": "Novi city",
        "counties": ["Oakland"],
        "page": NOVI,
        "agenda_is": "the meeting's own page",
    }
    assert (doc.raw_meta["meeting_date"], doc.raw_meta["date_from"]) == ("2026-11-09", "address")
    assert doc.raw_meta["original_kept"] is False
    # The page for the meeting to come holds no agenda yet. The run log names it.
    assert sink.runs[1]["detail"] == {
        "governments": 1,
        "meeting_pages_with_no_agenda": [NOVI_COMING],
    }


def test_an_agenda_written_on_a_page_is_read_for_signals_like_a_file(tmp_path):
    from pipeline.signals import Doc, Rules, process

    sink, rules = MemorySink(), Rules()
    run(meeting_web(), sink, tmp_path, pages=(CLEARED[NOVI],))
    stored = next(d for d in sink.documents.values() if d.url == NOVI_MEETING)

    def read(text: str):
        s = stored
        return process(
            Doc(s.source_id, s.url, s.retrieved_at, s.sha256, text, s.raw_meta, b""), rules
        )

    # The real agenda of November 9 uses none of the radar's terms.
    assert read(stored.text).counts()["signals"] == 0
    # The same page with one made-up item added.
    (draft,) = read(
        stored.text + "\nConsideration of a rezoning for a proposed data center."
    ).drafts
    assert draft.summary == (
        'An agenda that Novi posted for a meeting of November 9, 2026 uses the words "data center".'
    )
    assert draft.county_fips == "26125"  # Oakland County


def test_a_meetings_page_that_links_its_agenda_file_has_the_file_fetched(tmp_path):
    site, sink = meeting_web(), MemorySink()
    summary = run(site, sink, tmp_path, pages=(CLEARED[HEATH],))
    assert summary.status == "ok", summary.error
    assert site.page_urls() == [HEATH, HEATH_MEETING, HEATH_FILE]
    docs = {d.url: d for d in sink.documents.values()}
    file = docs[HEATH_FILE]
    assert "rezoning" in file.text
    assert (file.raw_meta["record"], file.raw_meta["page"]) == ("agenda_file", HEATH)
    assert file.raw_meta["meeting_page"] == HEATH_MEETING
    assert (file.raw_meta["meeting_date"], file.raw_meta["date_from"]) == (
        "2026-11-09",
        "link_text",
    )
    # The meeting's page is stored as the list of agenda links on it, not as an agenda.
    listing = json.loads(LocalArchive(tmp_path).get(docs[HEATH_MEETING].storage_path))
    assert docs[HEATH_MEETING].raw_meta["record"] == "meeting_page"
    assert [a["url"] for a in listing["agendas"]] == [HEATH_FILE]
    assert sink.runs[1]["detail"] == {"governments": 1}


def test_an_agenda_file_on_another_host_is_named_and_not_asked_for(tmp_path):
    older = "https://www.cityofotsego.org/document/november-2-2026-city-commission-agenda/"
    site = Site(
        {
            OTSEGO: httpx.Response(200, content=OTSEGO_BODY, headers=HTML),
            OTSEGO_MEETING: httpx.Response(200, content=OTSEGO_MEETING_BODY, headers=HTML),
            older: httpx.Response(200, content=OTSEGO_MEETING_BODY, headers=HTML),
        }
    )
    sink = MemorySink()
    summary = run(site, sink, tmp_path, pages=(CLEARED[OTSEGO],))
    assert summary.status == "ok", summary.error
    assert site.page_urls() == [OTSEGO, OTSEGO_MEETING, older]
    assert sink.runs[1]["detail"]["agenda_links_on_other_hosts"] == {OTSEGO: [OTSEGO_FILE]}


def test_a_meetings_page_whose_links_name_no_file_gives_nothing_and_is_named(tmp_path):
    site = Site(
        {
            LYNDON: httpx.Response(200, content=LYNDON_BODY, headers=HTML),
            LYNDON_MEETING: httpx.Response(200, content=LYNDON_MEETING_BODY, headers=HTML),
        }
    )
    collector_pages = (CLEARED[LYNDON],)
    sink = MemorySink()
    summary = run(site, sink, tmp_path, pages=collector_pages)
    # Three posts are in the last three weeks. Two have no saved page here, and fail.
    assert LYNDON_MEETING in site.page_urls() and summary.status == "partial"
    assert not [u for u in site.page_urls() if "/download/" in u]
    assert sink.runs[1]["detail"]["meeting_pages_with_no_agenda"] == [LYNDON_MEETING]


def test_a_meetings_link_that_turns_out_to_be_the_file_is_kept_as_the_agenda(tmp_path):
    """A made-up site. Some lists link a download address that has no file type and serves the
    agenda itself. The run by hand of November 24, 2026 followed one, on Holly's site, and
    kept nothing of what came back."""
    listing = "https://www.example-village.org/council-agendas/2026-agendas"
    download = (
        "https://www.example-village.org/council-agendas/"
        "november-10-2026-village-council-agenda/download"
    )
    page = (
        "<html><head><title>2026 Agendas</title></head><body><table><tr><td>"
        f'<a href="{download}">November 10, 2026 Village Council Agenda</a>'
        "</td></tr></table></body></html>"
    )
    site = Site(
        {
            listing: httpx.Response(200, content=page.encode(), headers=HTML),
            download: httpx.Response(200, content=agenda(3), headers=PDF),
        }
    )
    sink = MemorySink()
    village = Page(listing, "Example village", ("Oakland",), ("Example Village Council",))
    summary = run(site, sink, tmp_path, pages=(village,))
    assert summary.status == "ok", summary.error
    assert site.page_urls() == [listing, download]
    file = next(d for d in sink.documents.values() if d.url == download)
    assert "rezoning" in file.text
    kept = {k: file.raw_meta[k] for k in ("record", "government", "page", "meeting_date", "kind")}
    assert kept == {
        "record": "agenda_file",
        "government": "Example village",
        "page": listing,
        "meeting_date": "2026-11-10",
        "kind": "pdf",
    }
    assert sink.runs[1]["detail"] == {"governments": 1}
    # It is not asked for again.
    again = Site({listing: httpx.Response(200, content=page.encode(), headers=HTML)})
    run(again, sink, tmp_path, pages=(village,))
    assert again.page_urls() == [listing]


def test_a_past_meetings_page_is_not_asked_for_again_and_a_meeting_to_come_is(tmp_path):
    sink = MemorySink()
    run(meeting_web(), sink, tmp_path, pages=(CLEARED[NOVI],))
    again = meeting_web()
    summary = run(again, sink, tmp_path, pages=(CLEARED[NOVI],))
    # November 9 is past and stored. November 23 is the day of the run: its agenda may come.
    assert again.page_urls() == [NOVI, NOVI_COMING]
    assert (summary.status, summary.documents_new) == ("ok", 0)


def test_at_most_four_meeting_pages_are_followed_from_one_list(tmp_path):
    site = Site({OTSEGO: httpx.Response(200, content=OTSEGO_BODY, headers=HTML)})
    collector = MichiganAgendaPages(pages=(CLEARED[OTSEGO],), today=TODAY)
    assert collector.max_meeting_pages_per_page == 4
    collector.back_days = 400
    clock = FakeClock()
    with Fetcher(
        cleared_to_run(), contact=CONTACT, transport=site.transport, clock=clock, sleep=clock.sleep
    ) as fetcher:
        collector.run(
            source=cleared_to_run(), fetcher=fetcher, store=LocalArchive(tmp_path),
            sink=MemorySink(),
        )  # fmt: skip
    assert len(site.page_urls()) == 1 + 4


# --- not yet ------------------------------------------------------------------------------------


def test_no_job_can_start_the_source_while_it_is_marked_manual():
    # The collector is written and is not on the list of collectors a job can run. It goes on
    # that list, with a workflow file, when the owner says to run it.
    assert source().method == "manual" and "mi_agendas_own_sites" not in runner.REGISTRY
    with pytest.raises(runner.CannotStart):
        runner.run_source(source(), dry_run=True, contact=CONTACT)
    with pytest.raises(NotPermitted, match="collected by a person"):
        Fetcher(source(), contact=CONTACT)
