"""The own-sites agenda collector for Michigan, run against saved pages.

Ten real pages, saved on November 23, 2026 with one identified request each and cut down to the
part that lists agendas. Each fixture's .meta.json says so. Every one is a page the agenda
inventory clears, of a governing body, and between them they cover the six counties. No test
here touches the network.

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
    cleared_pages,
    find_agenda_links,
    find_date,
)
from pipeline.config import load_sources
from pipeline.store import MemorySink

from .helpers import CONTACT, FakeClock, Site, make_pdf

FIXTURES = Path(__file__).parent / "fixtures" / "mi_agendas_own_sites"
TODAY = dt.date(2026, 11, 23)
NAMES = (
    "allegan", "auburn-hills", "chelsea", "comstock", "erie",
    "luna-pier", "novi", "oshtemo", "river-rouge", "superior",
)  # fmt: skip
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
    assert sorted(p.name.removesuffix(".meta.json") for p in FIXTURES.glob("*.meta.json")) == list(
        NAMES
    )
    counties = set()
    for name in NAMES:
        m = meta(name)
        assert m["source_id"] == "mi_agendas_own_sites"
        assert m["trimmed"] is True and m["bytes"] < m["original_bytes"]
        assert m["url"] == m["final_url"]  # none of the ten redirected
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


def test_a_link_with_no_host_is_joined_to_the_pages_own_address():
    found = links("allegan")
    assert days("allegan")[:2] == ["2026-11-23", "2026-11-09"]
    assert len(found) == 6
    assert found[0].url == (
        "https://www.cityofallegan.org/government/city_council/"
        "11-23-26%20Regular%20Meeting%20Agenda.pdf?t=202611191806150"
    )
    # A file's name can start with something else: "4A 11-09-26 Regular Meeting Agenda.pdf".
    assert "/4A%2011-09-26%20Regular" in found[1].url


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
    """Novi's list links each agenda to a page of its own. The collector reads files only.

    So Novi's agendas are not read as the collector stands. The run log names the page.
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
    assert (len(CLEARED), len(governments)) == (145, 76)
    assert {"Chelsea city", "Novi city", "Pontiac city", "Oshtemo charter township"} <= governments
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
PAGES = (CLEARED[COMSTOCK], CLEARED[ERIE], CLEARED[NOVI])
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
        NOVI: httpx.Response(200, content=NOVI_BODY, headers=html),
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
    assert site.page_urls() == [COMSTOCK, ERIE, NOVI, *COMSTOCK_FILES, *ERIE_FILES]
    assert (summary.documents_seen, summary.documents_new) == (6, 6)
    assert all(r.headers["user-agent"].startswith("DataCenterRadar/") for r in site.requests)
    assert {d.source_id for d in sink.documents.values()} == {"mi_agendas_own_sites"}


def test_a_page_that_gives_no_file_is_named_in_the_run_log(tmp_path):
    sink = MemorySink()
    run(web(), sink, tmp_path)
    assert sink.runs[1]["detail"] == {"governments": 3, "pages_with_no_agenda_links": [NOVI]}


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
    assert again.page_urls() == [COMSTOCK, ERIE, NOVI]
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
    """
    file = "https://www.city-chelsea.org/11.09.26%20Agenda.pdf?t=202611051031130"
    kept_at = "https://cms3.revize.com/revize/chelseami/11.09.26%20Agenda.pdf?t=202611051031130"
    site = web()
    site.routes[CHELSEA] = httpx.Response(200, content=CHELSEA_BODY)
    site.routes[file] = httpx.Response(302, headers={"Location": kept_at})
    site.routes[kept_at] = httpx.Response(200, content=agenda(9), headers=PDF)
    site.routes["https://cms3.revize.com/robots.txt"] = httpx.Response(200, text=REVIZE_ROBOTS)
    sink = MemorySink()
    summary = run(site, sink, tmp_path, pages=(CLEARED[CHELSEA], CLEARED[ERIE]))
    assert summary.status == "partial"
    assert kept_at not in site.page_urls()
    assert list(sink.runs[1]["detail"]["refused_hosts"]) == ["www.city-chelsea.org"]
    assert (
        "robots.txt does not allow"
        in sink.runs[1]["detail"]["refused_hosts"]["www.city-chelsea.org"]
    )
    # The list is still read and stored, and the other site's files are fetched.
    assert {d.url for d in sink.documents.values()} == {CHELSEA, ERIE, *ERIE_FILES}


# --- not yet ------------------------------------------------------------------------------------


def test_no_job_can_start_the_source_while_it_is_marked_manual():
    # The collector is written and is not on the list of collectors a job can run. It goes on
    # that list, with a workflow file, when the owner says to run it.
    assert source().method == "manual" and "mi_agendas_own_sites" not in runner.REGISTRY
    with pytest.raises(runner.CannotStart):
        runner.run_source(source(), dry_run=True, contact=CONTACT)
    with pytest.raises(NotPermitted, match="collected by a person"):
        Fetcher(source(), contact=CONTACT)
