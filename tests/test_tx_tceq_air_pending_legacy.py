"""The TCEQ pending air permit lists, run against saved copies of TCEQ's two pages.

Both pages were saved with collectors.capture. Their .meta.json files hold the URL, the
retrieval time and the hash. The New Source Review page named two people as applicants. The
saved copy replaces those names, and its .meta.json says so. No test here touches the network.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections import Counter
from pathlib import Path

import httpx
import pytest

from collectors.base import Fetcher, LayoutChanged, LocalArchive
from collectors.tx.tceq_air_pending_legacy import (
    NSR,
    TITLE_V,
    TceqAirPendingLegacy,
    parse_list,
)
from pipeline.config import load_sources
from pipeline.store import MemorySink

from .helpers import CONTACT, FakeClock, Site

FIXTURES = Path(__file__).parent / "fixtures" / "tx_tceq_air_pending_legacy"
FILES = "https://www.tceq.texas.gov/assets/public/permitting/air/reports/applications/"


def fixture(name: str) -> tuple[bytes, dict]:
    body = (FIXTURES / f"{name}.html").read_bytes()
    return body, json.loads((FIXTURES / f"{name}.meta.json").read_text())


NSR_BODY, NSR_META = fixture("nsr-pending-permits")
TV_BODY, TV_META = fixture("titlev-pending-permits")

# The group for all agents in TCEQ's robots file, as read on November 20, 2026.
ROBOTS = "\n".join(
    [
        "User-agent: *",
        "Disallow: /@@tceq-search",
        "Disallow: /@@search",
        "Disallow: /search",
        "Disallow: /tceq-search",
        "Disallow: /portal_vocabularies",
        "",
    ]
)


def source():
    return load_sources().by_id("tx_tceq_air_pending_legacy")


# --- the saved copies ---------------------------------------------------------------------------


def test_the_fixtures_are_the_pages_the_collector_asks_for():
    assert (NSR_META["url"], TV_META["url"]) == (NSR, TITLE_V)
    assert hashlib.sha256(TV_BODY).hexdigest() == TV_META["sha256"]
    # The New Source Review copy differs from the page as retrieved by three replaced names.
    assert hashlib.sha256(NSR_BODY).hexdigest() == NSR_META["fixture_sha256"]
    assert NSR_META["fixture_sha256"] != NSR_META["sha256"]
    assert NSR_BODY.count(b"NAME REMOVED FROM FIXTURE") == 3


# --- the New Source Review list -----------------------------------------------------------------


def test_the_new_source_review_list():
    page = parse_list(NSR_BODY, NSR)
    assert page.title == "Pending Applications: New Source Review Permits"
    assert (page.data_updated, page.data_updated_text) == (dt.date(2026, 8, 28), "8/28/2026")
    assert len(page.rows) == 296
    assert Counter(row.section for row in page.rows) == {
        "NSR Case-by-Case Air Permits": 254,
        "Concrete Batch Plant Standard Permits": 37,
        "Standard Permits": 5,
    }
    assert Counter(row.stage for row in page.rows) == {
        "Administrative Complete Application": 246,
        "Technically Complete Application": 50,
    }


def test_a_row_is_read_as_the_page_shows_it():
    rows = {row.site: row for row in parse_list(NSR_BODY, NSR).rows}
    row = rows["ADC PLANO"]
    # The applicant cell also holds a link. Its text is not part of the name.
    assert row.applicant == "ALIGNED DATA CENTERS REIT LLC"
    assert row.permit_number == "131651"
    assert (row.received, row.received_text) == (dt.date(2026, 3, 30), "03/30/2026")
    assert row.stage == "Technically Complete Application"
    assert row.application_url == FILES + "407086-tc.pdf"
    assert row.notice_url == (
        "https://www.tceq.texas.gov/permitting/air/newsourcereview/"
        "airpermits-pendingpermit-apps#407086"
    )
    # One application can cover several permit numbers. The cell is kept whole.
    assert rows["LONGHORN DATA CENTER"].permit_number == "182126, GHGPSDTX263, PSDTX1688"


def test_addresses_broken_across_two_lines_are_joined():
    assert b"411117-ac.\r\npdf" in NSR_BODY
    page = parse_list(NSR_BODY, NSR)
    assert page.rows[0].application_url == FILES + "411117-ac.pdf"
    assert all(" " not in row.application_url for row in page.rows)
    assert len({row.application_url for row in page.rows}) == 296


def test_rows_without_a_notice_link():
    page = parse_list(NSR_BODY, NSR)
    last = page.rows[-1]
    assert (last.applicant, last.section, last.notice_url) == (
        "ZD SAND LLC",
        "Standard Permits",
        None,
    )
    assert sum(row.notice_url is None for row in page.rows) == 5


# --- the Title V list ---------------------------------------------------------------------------


def test_the_title_v_list():
    page = parse_list(TV_BODY, TITLE_V)
    assert page.title == "Pending Applications: Title V Operating Permits"
    assert page.data_updated == dt.date(2026, 11, 19)
    assert len(page.rows) == 328
    first = page.rows[0]
    assert (first.applicant, first.site, first.permit_number) == (
        "Acme Brick Company", "Denton Plant", "1605",
    )  # fmt: skip
    assert first.received == dt.date(2026, 7, 30)
    assert first.application_url == FILES + "40761-tc.pdf"
    # This list has letter headings only, and no notice links.
    assert {row.section for row in page.rows} == {""}
    assert {row.notice_url for row in page.rows} == {None}
    # It is still updated: it holds applications received after the other list was frozen.
    assert max(row.received for row in page.rows) == dt.date(2026, 11, 16)


# --- a changed layout ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "old,new",
    [
        (b"<h2>Pending Applications", b"<h3>Pending Applications"),
        (b"Data Updated:", b"Refreshed:"),
        (b'<th scope="col">Received Date</th>', b'<th scope="col">Date</th>'),
        (b"/reports/applications/407086-tc.pdf", b"/reports/other/407086-tc.pdf"),
    ],
)
def test_a_changed_layout_stops_the_parser(old, new):
    assert old in NSR_BODY
    with pytest.raises(LayoutChanged):
        parse_list(NSR_BODY.replace(old, new), NSR)


def test_a_row_with_a_missing_cell_stops_the_parser():
    old = b"<td>ADC PLANO</td>"
    assert NSR_BODY.count(old) == 1
    with pytest.raises(LayoutChanged):
        parse_list(NSR_BODY.replace(old, b""), NSR)


def test_an_unreadable_date_is_kept_as_text():
    body = TV_BODY.replace(b"<td>07/30/2026</td>", b"<td>July 2026</td>", 1)
    first = parse_list(body, TITLE_V).rows[0]
    assert (first.received, first.received_text) == (None, "July 2026")


# --- end to end ---------------------------------------------------------------------------------


def page_route(body: bytes, meta: dict, etag: str | None = None):
    """A list page with the validators TCEQ's file server sends."""
    etag = etag or meta["etag"]

    def route(request: httpx.Request) -> httpx.Response:
        if request.headers.get("If-None-Match") == etag:
            return httpx.Response(304)
        headers = {"Content-Type": meta["content_type"], "ETag": etag}
        return httpx.Response(200, content=body, headers=headers)

    return route


def site(robots: str = ROBOTS, routes: dict | None = None) -> Site:
    pages = {NSR: page_route(NSR_BODY, NSR_META), TITLE_V: page_route(TV_BODY, TV_META)}
    pages.update(routes or {})
    return Site(pages, robots=robots)


def run(tmp_path, sink, web: Site):
    clock = FakeClock()
    src = source()
    with Fetcher(
        src, contact=CONTACT, transport=web.transport, clock=clock, sleep=clock.sleep
    ) as fetcher:
        summary = TceqAirPendingLegacy().run(
            source=src, fetcher=fetcher, store=LocalArchive(tmp_path), sink=sink, runner="test"
        )
    return summary, clock


def test_the_source_is_cleared_for_the_fetcher():
    src = source()
    assert src.may_fetch_automatically
    assert (FIXTURES.parents[2] / "docs" / "sources" / f"{src.id}.md").exists()


def test_the_two_lists_and_nothing_else(tmp_path):
    sink, web = MemorySink(), site()
    summary, clock = run(tmp_path, sink, web)

    assert (summary.status, summary.documents_seen, summary.documents_new, summary.errors) == (
        "ok", 2, 2, 0,
    )  # fmt: skip
    # No application file is asked for, though the pages link 624 of them.
    assert web.page_urls() == [NSR, TITLE_V]
    assert all(pause >= 5 for pause in clock.sleeps)

    docs = {doc.url: doc for doc in sink.documents.values()}
    assert docs[TITLE_V].sha256 == TV_META["sha256"]
    assert LocalArchive(tmp_path).get(docs[NSR].storage_path) == NSR_BODY
    assert "LONGHORN DATA CENTER" in docs[NSR].text
    assert docs[NSR].retrieved_at.tzinfo is not None


def test_an_unchanged_file_costs_one_short_answer(tmp_path):
    sink = MemorySink()
    run(tmp_path, sink, site())

    web = site()
    again, _ = run(tmp_path, sink, web)

    assert (again.status, again.documents_seen, again.documents_new) == ("ok", 2, 0)
    requests = [r for r in web.requests if r.url.path != "/robots.txt"]
    assert [r.headers.get("If-None-Match") for r in requests] == [
        NSR_META["etag"],
        TV_META["etag"],
    ]


def test_a_page_rebuilt_with_the_same_rows_is_not_stored_again(tmp_path):
    sink = MemorySink()
    run(tmp_path, sink, site())

    # TCEQ rebuilds the New Source Review page every day. Only the "Report Run" date moves.
    rebuilt = NSR_BODY.replace(b"Report Run: 11/19/2026", b"Report Run: 11/20/2026")
    assert rebuilt != NSR_BODY
    web = site(routes={NSR: page_route(rebuilt, NSR_META, etag='"rebuilt"')})
    again, _ = run(tmp_path, sink, web)

    assert (again.status, again.documents_new) == ("ok", 0)
    assert len(sink.documents) == 2


def test_a_new_application_is_stored(tmp_path):
    sink = MemorySink()
    run(tmp_path, sink, site())

    changed = TV_BODY.replace(b"<td>Denton Plant</td>", b"<td>Example Plant</td>", 1)
    assert changed != TV_BODY
    web = site(routes={TITLE_V: page_route(changed, TV_META, etag='"changed"')})
    again, _ = run(tmp_path, sink, web)

    assert (again.status, again.documents_new) == ("ok", 1)
    assert len(sink.documents) == 3


def test_a_changed_layout_keeps_the_page_and_fails_the_run(tmp_path):
    sink = MemorySink()
    broken = NSR_BODY.replace(b"Data Updated:", b"Refreshed:")
    web = site(routes={NSR: page_route(broken, NSR_META)})
    summary, _ = run(tmp_path, sink, web)

    assert summary.status == "failed"
    assert "Data Updated" in summary.error
    assert web.page_urls() == [NSR]  # the run stopped there
    kept = {doc.url: doc for doc in sink.documents.values()}
    assert LocalArchive(tmp_path).get(kept[NSR].storage_path) == broken


def test_the_run_stops_if_robots_closes_the_folder(tmp_path):
    sink, web = MemorySink(), site(robots=ROBOTS + "Disallow: /assets/public/permitting\n")
    summary, _ = run(tmp_path, sink, web)
    assert summary.status == "blocked"
    assert web.page_urls() == [] and sink.documents == {}
