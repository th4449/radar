"""The ERCOT planning group collector, run against saved copies of ERCOT's pages.

The index and the two meeting pages were saved with collectors.capture. Their .meta.json files
hold the URL, the retrieval time and the hash. The files a meeting links to are 0.5 to 1.6 MB
each, too large to commit, so the end to end test serves small stand-in PDFs at their real
addresses. No test here touches the network.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import httpx
import pytest

from collectors.base import Fetcher, LayoutChanged, LocalArchive
from collectors.tx.ercot_rpg import INDEX, ErcotRpg, parse_index, parse_meeting
from pipeline.config import load_sources
from pipeline.store import MemorySink

from .helpers import CONTACT, FakeClock, Site, make_pdf

FIXTURES = Path(__file__).parent / "fixtures" / "tx_ercot_rpg"


def fixture(name: str) -> tuple[bytes, dict]:
    body = (FIXTURES / f"{name}.html").read_bytes()
    return body, json.loads((FIXTURES / f"{name}.meta.json").read_text())


INDEX_BODY, INDEX_META = fixture("rpg-index")
NOV_BODY, NOV_META = fixture("meeting-2026-11-03")
DEC_BODY, DEC_META = fixture("meeting-2026-12-15")
NOV, DEC = NOV_META["url"], DEC_META["url"]

FILES = [
    "https://www.ercot.com/files/docs/2026/11/02/3.-EIR-Status-Update-26RPG004-AEPSC-Laredo-Area-Upgrade-Project_NovRPG_Final.pdf",
    "https://www.ercot.com/files/docs/2026/11/02/4.-EIR_Southern_Spirit_Transmission_RPG_November_2026_Final.pdf",
    "https://www.ercot.com/files/docs/2026/11/02/5.-2026-Economic-Study-Nov-Update.pdf",
]

# The lines of ERCOT's robots file that matter here, as read on November 19, 2026.
ROBOTS = "\n".join(
    [
        "User-agent: *",
        "Disallow: /content/meetings",
        "Disallow: /content/committees",
        "Disallow: /widgets",
        "Disallow: /meetings",
        "Disallow: /misdownload",
        "Disallow: /ical",
        "",
    ]
)

# A day on which the November meeting is recent and the December meeting is two weeks away.
TODAY = dt.date(2026, 12, 1)


def source():
    return load_sources().by_id("tx_ercot_rpg")


# --- the index ----------------------------------------------------------------------------------


def test_the_index_lists_each_meeting_once():
    links = parse_index(INDEX_BODY)
    assert len(links) == 28
    assert len({link.url for link in links}) == 28
    assert links[0].url == "https://www.ercot.com/calendar/01062026-RPG-Meeting"
    assert (links[0].date, links[0].date_text) == (dt.date(2026, 1, 6), "Jan 06, 2026")
    assert NOV in {link.url for link in links} and DEC in {link.url for link in links}


def test_the_link_text_and_the_address_give_the_same_date():
    for link in parse_index(INDEX_BODY):
        assert link.date is not None
        assert link.date == link.slug_date


def test_the_index_parser_skips_the_closed_calendar_feed():
    assert b"webcal://www.ercot.com/ical/meetings" in INDEX_BODY
    assert all("/calendar/" in link.url for link in parse_index(INDEX_BODY))


def test_an_index_with_no_meetings_stops_the_parser():
    with pytest.raises(LayoutChanged):
        parse_index(INDEX_BODY.replace(b"-RPG-Meeting", b"-Other-Meeting"))


# --- a meeting page -----------------------------------------------------------------------------


def test_a_meeting_with_files():
    meeting = parse_meeting(NOV_BODY, NOV)
    assert meeting.title == "RPG Meeting - Webex Only"
    assert (meeting.date, meeting.date_text) == (dt.date(2026, 11, 3), "November 03, 2026")
    assert meeting.topics[2] == "EIR Status Update – 26RPG004 AEPSC Laredo Area Upgrade Project"
    assert len(meeting.topics) == 6
    assert [f.url for f in meeting.files] == FILES
    first = meeting.files[0]
    assert first.section == "Key Documents"
    assert (first.caption, first.posted) == ("Nov 2, 2026 - pdf - 1.6 MB", dt.date(2026, 11, 2))
    assert meeting.files[1].title == "4. EIR Southern Spirit Transmission"


def test_a_meeting_with_nothing_posted_yet():
    meeting = parse_meeting(DEC_BODY, DEC)
    assert (meeting.title, meeting.date) == ("RPG Meeting", dt.date(2026, 12, 15))
    assert meeting.topics == () and meeting.files == ()


def test_only_files_on_ercots_site_are_listed():
    # The page also links to a Webex room, the calendar feed and the committee widget.
    assert b"https://ercot.webex.com/ercot" in NOV_BODY
    assert b"/widgets/committee?find=rpg" in NOV_BODY
    for f in parse_meeting(NOV_BODY, NOV).files:
        assert f.url.startswith("https://www.ercot.com/files/docs/")


@pytest.mark.parametrize(
    "old,new",
    [
        (b'class="meeting_details"', b'class="event"'),
        (b'class="meeting-datetime pb-3"', b'class="when"'),
        (b'name="section"', b'name="block"'),
    ],
)
def test_a_changed_meeting_layout_stops_the_parser(old, new):
    assert old in NOV_BODY
    with pytest.raises(LayoutChanged):
        parse_meeting(NOV_BODY.replace(old, new), NOV)


def test_an_unreadable_date_is_kept_as_text():
    body = NOV_BODY.replace(b"<strong>November 03, 2026</strong>", b"<strong>Nov 032026</strong>")
    meeting = parse_meeting(body, NOV)
    assert (meeting.date, meeting.date_text) == (None, "Nov 032026")


# --- end to end ---------------------------------------------------------------------------------


def pdf_route(n: int):
    """A small stand-in for an ERCOT file, with the validators ERCOT's file server sends."""
    body = make_pdf([f"Stand-in for ERCOT planning group file {n}"])
    etag = f'"stand-in-{n}"'

    def route(request: httpx.Request) -> httpx.Response:
        if request.headers.get("If-None-Match") == etag:
            return httpx.Response(304)
        return httpx.Response(
            200, content=body, headers={"Content-Type": "application/pdf", "ETag": etag}
        )

    return route


def html(body: bytes, meta: dict, tracking: bytes = b"") -> httpx.Response:
    return httpx.Response(
        200, content=body + tracking, headers={"Content-Type": meta["content_type"]}
    )


def site(robots: str = ROBOTS, tracking: bytes = b"", routes: dict | None = None) -> Site:
    pages = {
        INDEX: html(INDEX_BODY, INDEX_META, tracking),
        NOV: html(NOV_BODY, NOV_META, tracking),
        DEC: html(DEC_BODY, DEC_META, tracking),
        **{url: pdf_route(n) for n, url in enumerate(FILES, start=3)},
    }
    pages.update(routes or {})
    return Site(pages, robots=robots)


def run(tmp_path, sink, web: Site, today: dt.date = TODAY):
    clock = FakeClock()
    src = source()
    with Fetcher(
        src, contact=CONTACT, transport=web.transport, clock=clock, sleep=clock.sleep
    ) as fetcher:
        summary = ErcotRpg(today=today, back_days=30, ahead_days=14).run(
            source=src, fetcher=fetcher, store=LocalArchive(tmp_path), sink=sink, runner="test"
        )
    return summary, clock


def test_the_source_is_cleared_for_the_fetcher():
    src = source()
    assert str(src.url) == INDEX == INDEX_META["url"]
    assert src.may_fetch_automatically
    assert (FIXTURES.parents[2] / "docs" / "sources" / f"{src.id}.md").exists()


def test_index_then_meetings_then_files(tmp_path):
    sink, web = MemorySink(), site()
    summary, clock = run(tmp_path, sink, web)

    assert (summary.status, summary.documents_seen, summary.documents_new, summary.errors) == (
        "ok", 6, 6, 0,
    )  # fmt: skip
    # Only the two meetings near today, in date order, then the files of the one that has any.
    assert web.page_urls() == [INDEX, NOV, DEC, *FILES]
    assert all(pause >= 5 for pause in clock.sleeps)

    docs = {doc.url: doc for doc in sink.documents.values()}
    assert docs[INDEX].sha256 == INDEX_META["sha256"]
    assert docs[NOV].sha256 == NOV_META["sha256"]
    assert LocalArchive(tmp_path).get(docs[NOV].storage_path) == NOV_BODY
    assert "Southern Spirit HVDC Study Scope" in docs[NOV].text
    assert docs[FILES[0]].raw_meta["kind"] == "pdf"
    assert "Stand-in for ERCOT planning group file 3" in docs[FILES[0]].text
    assert docs[FILES[0]].retrieved_at.tzinfo is not None


def test_a_second_run_stores_nothing_and_asks_for_each_file_conditionally(tmp_path):
    sink = MemorySink()
    run(tmp_path, sink, site())

    # ERCOT's pages carry tracking codes that differ on every request. The bytes change, the
    # content does not.
    web = site(tracking=b"<!-- rid=847215377 -->")
    again, _ = run(tmp_path, sink, web)

    assert (again.status, again.documents_seen, again.documents_new) == ("ok", 6, 0)
    assert len(sink.documents) == 6
    file_requests = [r for r in web.requests if "/files/docs/" in str(r.url)]
    assert len(file_requests) == 3
    assert all(r.headers.get("If-None-Match", "").startswith('"stand-in-') for r in file_requests)


def test_a_newly_posted_file_is_picked_up(tmp_path):
    sink = MemorySink()
    run(tmp_path, sink, site())

    extra = "https://www.ercot.com/files/docs/2026/11/04/6.-Example-Large-Load-Project.pdf"
    listed = NOV_BODY.replace(FILES[2].encode(), extra.encode())
    assert listed != NOV_BODY
    web = site(routes={NOV: html(listed, NOV_META), extra: pdf_route(6)})
    again, _ = run(tmp_path, sink, web)

    assert (again.status, again.documents_new) == ("ok", 2)  # the meeting page and the file
    assert extra in {doc.url for doc in sink.documents.values()}


def test_meetings_outside_the_window_are_left_alone(tmp_path):
    web = site()
    summary, _ = run(tmp_path, MemorySink(), web, today=dt.date(2026, 11, 20))
    # October 20 is 31 days back and December 15 is 25 days ahead. Only November 3 is read.
    assert web.page_urls() == [INDEX, NOV, *FILES]
    assert summary.status == "ok"


def test_the_collector_never_asks_for_a_closed_path(tmp_path):
    web = site()
    run(tmp_path, MemorySink(), web)
    for url in web.page_urls():
        path = httpx.URL(url).path
        assert not path.startswith(("/widgets", "/meetings", "/ical", "/misdownload", "/content/"))


def test_a_changed_layout_keeps_the_page_and_fails_the_run(tmp_path):
    sink = MemorySink()
    broken = NOV_BODY.replace(b'class="meeting_details"', b'class="event"')
    web = site(routes={NOV: html(broken, NOV_META)})
    summary, _ = run(tmp_path, sink, web)

    assert summary.status == "failed"
    assert "no meeting details block" in summary.error
    assert web.page_urls() == [INDEX, NOV]  # the run stopped there
    kept = {doc.url: doc for doc in sink.documents.values()}
    assert LocalArchive(tmp_path).get(kept[NOV].storage_path) == broken


def test_the_run_stops_if_robots_closes_the_committee_pages(tmp_path):
    sink, web = MemorySink(), site(robots=ROBOTS + "Disallow: /committees\n")
    summary, _ = run(tmp_path, sink, web)
    assert summary.status == "blocked"
    assert web.page_urls() == [] and sink.documents == {}


# --- a one-time history run, for the backtest ----------------------------------------------------

YEAR_2025 = f"{INDEX}/2025"
JULY_2025 = "https://www.ercot.com/calendar/07292025-RPG-Meeting"
YEAR_BODY = (
    b"<html><body><main><ul>"
    b'<li><a href="/calendar/07292025-RPG-Meeting">July 29, 2025</a></li>'
    b'<li><a href="/calendar/12162024-RPG-Meeting">December 16, 2024</a></li>'
    b"</ul></main></body></html>"
)


def history_run(tmp_path, sink, web: Site, since: dt.date):
    clock = FakeClock()
    src = source()
    with Fetcher(
        src, contact=CONTACT, transport=web.transport, clock=clock, sleep=clock.sleep
    ) as fetcher:
        return ErcotRpg.history(since, today=TODAY).run(
            source=src, fetcher=fetcher, store=LocalArchive(tmp_path), sink=sink, runner="test"
        )


def history_site() -> Site:
    # Every other meeting on the saved index answers as one with nothing posted.
    others = {
        link.url: html(DEC_BODY, DEC_META)
        for link in parse_index(INDEX_BODY)
        if link.url not in (NOV, DEC)
    }
    return site(
        routes={
            **others,
            YEAR_2025: html(YEAR_BODY, INDEX_META),
            # The older meeting lists the same three files as November's. Each is asked once.
            JULY_2025: html(NOV_BODY, NOV_META),
        }
    )


def test_a_history_run_reads_the_older_years_pages_and_every_meeting_since_its_first_day(tmp_path):
    web = history_site()
    summary = history_run(tmp_path, MemorySink(), web, dt.date(2025, 1, 1))
    asked = web.page_urls()
    # The index holds this year. Each earlier year has a page of its own.
    assert asked[:2] == [INDEX, YEAR_2025]
    assert JULY_2025 in asked and NOV in asked
    # A meeting before the first day is left alone, and so is a year before it.
    assert "https://www.ercot.com/calendar/12162024-RPG-Meeting" not in asked
    assert f"{INDEX}/2024" not in asked
    assert sorted(u for u in asked if "/files/docs/" in u) == sorted(FILES)
    assert summary.errors == 0


def test_a_history_run_that_is_started_again_does_not_ask_for_a_stored_file(tmp_path):
    sink = MemorySink()
    history_run(tmp_path, sink, history_site(), dt.date(2025, 1, 1))
    again = history_site()
    history_run(tmp_path, sink, again, dt.date(2025, 1, 1))
    assert not [u for u in again.page_urls() if "/files/docs/" in u]


def test_an_everyday_run_reads_no_older_years_page(tmp_path):
    web = history_site()
    run(tmp_path, MemorySink(), web)
    assert YEAR_2025 not in web.page_urls()
