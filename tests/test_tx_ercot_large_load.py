"""The ERCOT large load collector, run against saved copies of ERCOT's pages.

Four pages were saved with collectors.capture: the index and one meeting page for the Large
Load Working Group and for the Technical Advisory Committee. The files the meetings link to are
up to 4.4 MB each, too large to commit, so the end to end test serves small stand-ins at their
real addresses. No test here touches the network.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import httpx

from collectors.base import Fetcher, LocalArchive
from collectors.tx.ercot_large_load import LLWG, LLWG_INDEX, TAC, TAC_INDEX, ErcotLargeLoad
from collectors.tx.ercot_meetings import parse_index, parse_meeting
from pipeline.config import load_sources
from pipeline.store import MemorySink

from .helpers import CONTACT, FakeClock, Site, make_pdf, make_pptx, make_zip

FIXTURES = Path(__file__).parent / "fixtures" / "tx_ercot_large_load"


def fixture(name: str) -> tuple[bytes, dict]:
    body = (FIXTURES / f"{name}.html").read_bytes()
    return body, json.loads((FIXTURES / f"{name}.meta.json").read_text())


LLWG_INDEX_BODY, LLWG_INDEX_META = fixture("llwg-index")
LLWG_NOV_BODY, LLWG_NOV_META = fixture("llwg-2026-11-19")
TAC_INDEX_BODY, TAC_INDEX_META = fixture("tac-index")
TAC_NOV_BODY, TAC_NOV_META = fixture("tac-2026-11-18")
LLWG_NOV, TAC_NOV = LLWG_NOV_META["url"], TAC_NOV_META["url"]

DOCS = "https://www.ercot.com/files/docs/2026/11/"
LLWG_FILES = [
    DOCS + "19/Agenda-2026-Nov-LLWG__.xlsx",
    DOCS + "18/2.-261119-ERCOT-LLWG-NERC-Registration-Update.pdf",
    DOCS + "18/2.-NERC-Computational-Load-Update-for-ERCOT-LLWG-November.pdf",
    DOCS + "18/4.-BZ-VRT-Review-and-Next-Steps_Nov2026-LLWG.pdf",
    DOCS + "18/6.-ERCOT_LIOO_Portal_20261119.pptx",
]
TAC_FILE = DOCS + "18/10.-Large-Load-Issues.zip"

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

# The day after the working group met and two days after the committee met.
TODAY = dt.date(2026, 11, 20)


def source():
    return load_sources().by_id("tx_ercot_large_load")


# --- the two indexes ----------------------------------------------------------------------------


def test_the_working_group_index_lists_its_own_meetings_only():
    links = parse_index(LLWG_INDEX_BODY, LLWG)
    assert len(links) == 14
    assert all("-LLWG-Meeting" in link.url for link in links)
    assert LLWG_NOV in {link.url for link in links}
    # The page also links to meetings of other bodies, in a table about a study process.
    for other in (b"05132026-Special-TAC-Meeting", b"03052026-ROS-Meeting", b"adminmonitor.com"):
        assert other in LLWG_INDEX_BODY


def test_a_link_with_no_date_in_its_text_is_dated_from_its_address():
    by_url = {link.url: link for link in parse_index(LLWG_INDEX_BODY, LLWG)}
    link = by_url["https://www.ercot.com/calendar/01222026-LLWG-Meeting"]
    assert (link.date, link.date_text, link.slug_date) == (
        None, "Link to Meeting", dt.date(2026, 1, 22),
    )  # fmt: skip


def test_the_committee_index_includes_special_and_webex_meetings():
    links = parse_index(TAC_INDEX_BODY, TAC)
    assert len(links) == 22
    urls = {link.url for link in links}
    assert "https://www.ercot.com/calendar/05062026-Special-TAC-Meeting" in urls
    assert "https://www.ercot.com/calendar/06302026-TAC-Meeting-_-Webex" in urls
    assert TAC_NOV in urls
    assert all(link.date == link.slug_date for link in links)


# --- the two meeting pages ----------------------------------------------------------------------


def test_every_file_of_a_working_group_meeting_is_wanted():
    meeting = parse_meeting(LLWG_NOV_BODY, LLWG_NOV)
    assert (meeting.title, meeting.date) == ("LLWG Meeting", dt.date(2026, 11, 19))
    assert [f.url for f in meeting.files] == LLWG_FILES
    assert LLWG.files is None


def test_only_the_large_load_file_of_a_committee_meeting_is_wanted():
    meeting = parse_meeting(TAC_NOV_BODY, TAC_NOV)
    assert (meeting.title, meeting.date) == ("TAC Meeting", dt.date(2026, 11, 18))
    assert "Large Load Issues" in meeting.topics
    assert len(meeting.files) == 14
    wanted = [f for f in meeting.files if TAC.files.search(f.title)]
    assert [(f.title, f.url) for f in wanted] == [("10. Large Load Issues", TAC_FILE)]
    assert wanted[0].caption == "Nov 18, 2026 - zip - 4.4 MB"


def test_the_title_filter_reads_the_ways_ercot_writes_the_words():
    for title in (
        "10. Large Load Issues",
        "Large_Load_Interconnection_Status",
        "LARGE-LOAD update",
    ):
        assert TAC.files.search(title)
    for title in ("7. ROS Report", "PGRR122 Loss of Load ballot", "11. ERCOT Reports"):
        assert not TAC.files.search(title)


# --- end to end ---------------------------------------------------------------------------------


def file_route(n: int, url: str):
    """A small stand-in for an ERCOT file, with the validators ERCOT's file server sends."""
    words = f"Stand-in for ERCOT large load file {n}"
    if url.endswith(".pdf"):
        body, ctype = make_pdf([words]), "application/pdf"
    elif url.endswith(".pptx"):
        body, ctype = make_pptx([words]), "application/octet-stream"
    elif url.endswith(".zip"):
        # In November 2026 the committee's update was one slide deck inside a zip file.
        body, ctype = make_zip({"10. TAC update.pptx": make_pptx([words])}), "application/zip"
    else:
        body, ctype = make_zip({"xl/workbook.xml": b"<workbook/>"}), "application/octet-stream"
    etag = f'"stand-in-{n}"'

    def route(request: httpx.Request) -> httpx.Response:
        if request.headers.get("If-None-Match") == etag:
            return httpx.Response(304)
        return httpx.Response(200, content=body, headers={"Content-Type": ctype, "ETag": etag})

    return route


def html(body: bytes, meta: dict, tracking: bytes = b"") -> httpx.Response:
    return httpx.Response(
        200, content=body + tracking, headers={"Content-Type": meta["content_type"]}
    )


def site(tracking: bytes = b"") -> Site:
    pages = {
        LLWG_INDEX: html(LLWG_INDEX_BODY, LLWG_INDEX_META, tracking),
        TAC_INDEX: html(TAC_INDEX_BODY, TAC_INDEX_META, tracking),
        LLWG_NOV: html(LLWG_NOV_BODY, LLWG_NOV_META, tracking),
        TAC_NOV: html(TAC_NOV_BODY, TAC_NOV_META, tracking),
        **{url: file_route(n, url) for n, url in enumerate([*LLWG_FILES, TAC_FILE])},
    }
    return Site(pages, robots=ROBOTS)


def run(tmp_path, sink, web: Site, back_days: int = 10):
    clock = FakeClock()
    src = source()
    with Fetcher(
        src, contact=CONTACT, transport=web.transport, clock=clock, sleep=clock.sleep
    ) as fetcher:
        summary = ErcotLargeLoad(today=TODAY, back_days=back_days).run(
            source=src, fetcher=fetcher, store=LocalArchive(tmp_path), sink=sink, runner="test"
        )
    return summary, clock


def test_the_source_is_cleared_for_the_fetcher():
    src = source()
    assert src.may_fetch_automatically
    assert src.layer == "context"
    assert (FIXTURES.parents[2] / "docs" / "sources" / f"{src.id}.md").exists()


def test_the_default_window_reaches_back_past_a_month():
    collector = ErcotLargeLoad(today=TODAY)
    assert (collector.back_days, collector.ahead_days) == (45, 14)


def test_both_indexes_then_meetings_then_the_wanted_files(tmp_path):
    sink, web = MemorySink(), site()
    summary, clock = run(tmp_path, sink, web)

    assert (summary.status, summary.documents_seen, summary.documents_new, summary.errors) == (
        "ok", 10, 10, 0,
    )  # fmt: skip
    assert web.page_urls() == [LLWG_INDEX, TAC_INDEX, LLWG_NOV, TAC_NOV, *LLWG_FILES, TAC_FILE]
    assert all(pause >= 5 for pause in clock.sleeps)

    docs = {doc.url: doc for doc in sink.documents.values()}
    assert docs[TAC_NOV].sha256 == TAC_NOV_META["sha256"]
    assert "Stand-in for ERCOT large load file 1" in docs[LLWG_FILES[1]].text
    # The slide deck is read, and so is the deck inside the committee's zip file.
    assert docs[LLWG_FILES[4]].raw_meta["kind"] == "pptx"
    assert docs[LLWG_FILES[4]].text == "Stand-in for ERCOT large load file 4"
    assert docs[TAC_FILE].raw_meta["kind"] == "zip"
    assert docs[TAC_FILE].text == "File: 10. TAC update.pptx\nStand-in for ERCOT large load file 5"
    assert docs[TAC_FILE].storage_path.endswith(".zip")


def test_the_other_thirteen_committee_files_are_never_asked_for(tmp_path):
    web = site()
    run(tmp_path, MemorySink(), web)
    asked = set(web.page_urls())
    others = [f.url for f in parse_meeting(TAC_NOV_BODY, TAC_NOV).files if f.url != TAC_FILE]
    assert len(others) == 13
    assert asked.isdisjoint(others)


def test_a_second_run_stores_nothing_and_asks_for_each_file_conditionally(tmp_path):
    sink = MemorySink()
    run(tmp_path, sink, site())

    web = site(tracking=b"<!-- rid=847215377 -->")
    again, _ = run(tmp_path, sink, web)

    assert (again.status, again.documents_seen, again.documents_new) == ("ok", 10, 0)
    assert len(sink.documents) == 10
    file_requests = [r for r in web.requests if "/files/docs/" in str(r.url)]
    assert len(file_requests) == 6
    assert all(r.headers.get("If-None-Match", "").startswith('"stand-in-') for r in file_requests)


def test_a_meeting_page_that_is_missing_is_counted_and_the_run_goes_on(tmp_path):
    # With the default window the October meetings are in range. They are not saved here, so
    # the fake site answers 404 for them.
    sink, web = MemorySink(), site()
    summary, _ = run(tmp_path, sink, web, back_days=45)
    assert summary.status == "partial"
    assert summary.errors == 2
    assert "https://www.ercot.com/calendar/10152026-LLWG-Meeting" in web.page_urls()
    assert "https://www.ercot.com/calendar/10282026-TAC-Meeting" in web.page_urls()
    assert len(sink.documents) == 10
