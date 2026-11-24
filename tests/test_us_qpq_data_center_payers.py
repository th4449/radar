"""The collector for the QPQ Tracker study's list of payers, run against a saved copy.

The fixture is the real page's table of payers, saved once with collectors.capture and cut down
to that table. Its .meta.json holds the URL, the retrieval time and both hashes. No test here
touches the network.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import httpx
import pytest

from collectors.base import Fetcher, LocalArchive, NotPermitted, RobotsDisallowed
from collectors.run import REGISTRY
from collectors.us.qpq_data_center_payers import (
    URL,
    LayoutChanged,
    Payer,
    QpqDataCenterPayers,
    parse,
)
from pipeline.config import load_sources
from pipeline.store import MemorySink

from .helpers import CONTACT, FakeClock, Site

SOURCE_ID = "us_qpq_data_center_payers"
FIXTURES = Path(__file__).parent / "fixtures" / SOURCE_ID
BODY = (FIXTURES / "data-centers-payers.html").read_bytes()
META = json.loads((FIXTURES / "data-centers-payers.meta.json").read_text())

# The site's robots file for every agent, as read on November 24, 2026.
ROBOTS = (
    "User-Agent: *\nAllow: /\nDisallow: /compare\nDisallow: /money-flow\n"
    "Disallow: /israel-lobby\nDisallow: /sectors/\nDisallow: /api/\n"
)


def source():
    """The source as it will stand once the owner says to run it. Today it is manual."""
    return load_sources().by_id(SOURCE_ID).model_copy(update={"method": "http"})


# --- the parser ---------------------------------------------------------------------------------


def test_every_payer_is_read():
    rows = parse(BODY)
    assert len(rows) == META["rows_kept"] == 61
    assert Counter(r.payer_class for r in rows) == {
        "Utility": 35,
        "Trade group, developer, pipeline or investor": 12,
        "Data center operator": 8,
        "Hyperscaler": 6,
    }


def test_the_rows_add_up_to_the_figures_the_page_gives():
    # The full page, read the same day, says $148.4M in 16,389 contributions.
    rows = parse(BODY)
    assert sum(r.direct_giving for r in rows) == 148_392_563
    assert sum(r.contributions for r in rows) == 16_389


def test_a_plain_row():
    assert parse(BODY)[0] == Payer(
        name="Dominion Energy",
        url="https://www.purchasingpolicy.org/entity/d16a74ba-38f5-4791-bed7-8584adf8590b",
        payer_class="Utility",
        direct_giving=33_720_558,
        contributions=997,
        states=("VA",),
    )


def test_a_row_with_several_states_and_a_joined_name():
    rows = {r.name: r for r in parse(BODY)}
    assert rows["Google"].states == ("CA", "GA", "IL", "MI", "OR", "PA", "TN", "TX", "VA")
    # The study's own label, kept as written. Matching by name is pipeline/study.py's work.
    assert rows["CMS / Consumers Energy"].states == ("MI",)
    assert rows["Walbridge"].direct_giving == 50


@pytest.mark.parametrize(
    "old,new",
    [
        (b">Direct giving</th>", b">Total</th>"),
        (b"<table", b"<div"),
        (b"<summary", b"<p"),
        (b"$33,720,558", b"about $33.7M"),
        (b"/entity/d16a74ba-38f5-4791-bed7-8584adf8590b", b"/entity/dominion"),
        (b">VA</td>", b">Virginia</td>"),
    ],
)
def test_a_changed_layout_stops_the_parser(old, new):
    assert old in BODY
    with pytest.raises(LayoutChanged):
        parse(BODY.replace(old, new, 1))


def test_a_table_shorter_than_the_page_says_stops_the_parser():
    start = BODY.index(b"<tr", BODY.index(b"<tbody"))
    end = BODY.index(b"</tr>", start) + len(b"</tr>")
    with pytest.raises(LayoutChanged, match="61 payers and the table has 60"):
        parse(BODY[:start] + BODY[end:])


# --- the source and its rules -------------------------------------------------------------------


def test_the_source_is_manual_and_no_job_reads_it():
    src = load_sources().by_id(SOURCE_ID)
    assert str(src.url) == URL == META["url"]
    assert src.method == "manual" and not src.may_fetch_automatically
    assert SOURCE_ID not in REGISTRY
    assert (FIXTURES.parents[2] / "docs" / "sources" / f"{SOURCE_ID}.md").exists()
    with pytest.raises(NotPermitted):
        Fetcher(src, contact=CONTACT)


def test_the_sites_robots_file_allows_the_page_and_bars_its_api():
    clock = FakeClock()
    api = "https://www.purchasingpolicy.org/api/v1/search?q=oncor"
    web = Site(
        {URL: httpx.Response(200, content=BODY), api: httpx.Response(200, json=[])}, robots=ROBOTS
    )
    with Fetcher(
        source(), contact=CONTACT, transport=web.transport, clock=clock, sleep=clock.sleep
    ) as fetcher:
        assert fetcher.get(URL).body == BODY
        with pytest.raises(RobotsDisallowed):
            fetcher.get(api)
    assert web.page_urls() == [URL]


# --- end to end ---------------------------------------------------------------------------------


def run(tmp_path, sink, robots=ROBOTS, body=BODY):
    clock = FakeClock()
    web = Site(
        {URL: httpx.Response(200, content=body, headers={"Content-Type": META["content_type"]})},
        robots=robots,
    )
    src = source()
    with Fetcher(
        src, contact=CONTACT, transport=web.transport, clock=clock, sleep=clock.sleep
    ) as fetcher:
        summary = QpqDataCenterPayers().run(
            source=src, fetcher=fetcher, store=LocalArchive(tmp_path), sink=sink, runner="test"
        )
    return summary, web


def test_the_page_is_archived_end_to_end(tmp_path):
    sink = MemorySink()
    summary, web = run(tmp_path, sink)

    assert (summary.status, summary.documents_seen, summary.documents_new, summary.errors) == (
        "ok", 1, 1, 0,
    )  # fmt: skip
    assert web.page_urls() == [URL]
    (doc,) = sink.documents.values()
    assert doc.url == URL
    assert doc.sha256 == META["sha256"]
    assert doc.retrieved_at.tzinfo is not None
    stored = LocalArchive(tmp_path).get(doc.storage_path)
    assert stored == BODY
    assert parse(stored) == parse(BODY)

    again, _ = run(tmp_path, sink)
    assert (again.status, again.documents_seen, again.documents_new) == ("ok", 1, 0)


def test_a_rebuilt_page_with_the_same_table_is_not_stored_again(tmp_path):
    """The site's bytes change with every build. Only a change in the table is news."""
    sink = MemorySink()
    run(tmp_path, sink)
    rebuilt = BODY.replace(b"<title>", b"<title>Rebuilt. ")
    assert rebuilt != BODY and parse(rebuilt) == parse(BODY)
    summary, _ = run(tmp_path, sink, body=rebuilt)
    assert (summary.status, summary.documents_seen, summary.documents_new) == ("ok", 1, 0)

    changed = BODY.replace(b"$33,720,558", b"$33,720,559")
    summary, _ = run(tmp_path, sink, body=changed)
    assert (summary.status, summary.documents_new) == ("ok", 1)


def test_a_changed_layout_fails_the_run_and_keeps_the_page_for_a_person(tmp_path):
    sink = MemorySink()
    odd = BODY.replace(b">Direct giving</th>", b">Total</th>")
    summary, _ = run(tmp_path, sink, body=odd)
    assert summary.status == "failed"
    assert "expected one table of payers" in summary.error
    (doc,) = sink.documents.values()
    assert LocalArchive(tmp_path).get(doc.storage_path) == odd


def test_the_run_stops_if_robots_closes_the_page(tmp_path):
    sink = MemorySink()
    summary, web = run(tmp_path, sink, robots="User-agent: *\nDisallow: /data-centers\n")
    assert summary.status == "blocked"
    assert web.page_urls() == []
    assert sink.documents == {}
