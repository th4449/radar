"""The first real collector, run against a saved copy of the Comptroller's page.

The fixture was saved once with collectors.capture. Its .meta.json holds the URL, the retrieval
time and the hash. No test here touches the network.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import httpx
import pytest

from collectors.base import Fetcher, LocalArchive
from collectors.tx.comptroller_data_centers import (
    LARGE,
    QUALIFYING,
    URL,
    ComptrollerDataCenters,
    LayoutChanged,
    parse,
)
from pipeline.config import load_sources
from pipeline.store import MemorySink

from .helpers import CONTACT, FakeClock, Site

FIXTURES = Path(__file__).parent / "fixtures" / "tx_comptroller_data_centers"
BODY = (FIXTURES / "data-center-lists.html").read_bytes()
META = json.loads((FIXTURES / "data-center-lists.meta.json").read_text())

# The lines of the Comptroller's robots file that decide this URL, as read on November 19, 2026.
ROBOTS = "User-agent: *\nDisallow: /*/\nAllow: /taxes/\nAllow: /economy/\n"


def source():
    return load_sources().by_id("tx_comptroller_data_centers")


# --- the parser ---------------------------------------------------------------------------------


def test_both_tables_are_read():
    rows = parse(BODY)
    assert sum(r.program == QUALIFYING for r in rows) == 70
    assert sum(r.program == LARGE for r in rows) == 113
    assert all(r.name for r in rows)


def test_a_plain_row():
    first = parse(BODY)[0]
    assert first.program == QUALIFYING
    assert first.name == "1102 McKinzie LLC Data Center"
    assert first.effective_date == dt.date(2024, 2, 23)
    assert first.owners == ("1102 McKinzie LLC",)
    assert first.owner_registrations == ("DC832828-OW1",)
    assert first.operator_registrations == ("DC832828-OP1",)
    assert (first.exemption_end_date, first.exemption_end_date_text) == (None, "")


def test_a_row_with_several_operators_and_no_owner():
    row = next(r for r in parse(BODY) if r.name == "3301 Hibbetts Road Data Center")
    assert row.owners == () and row.owner_registrations == ()
    assert row.occupants == ("Coreweave, Inc.",)
    assert row.operators == (
        "Core Scientific, Inc.",
        "Coreweave Compute Acquisition Co. II. LLC",
        "CCAC IV.II, LLC",
    )
    assert row.operator_registrations == ("DC481494-OP1", "DC481494-OP2", "DC481494-OP3")


def test_a_row_with_the_last_cell_missing_is_still_read():
    row = next(r for r in parse(BODY) if r.name == "Pecos Ranch Data Center")
    assert row.program == LARGE
    assert row.effective_date == dt.date(2026, 8, 10)
    assert row.operator_registrations == ("LD547974-OP1",)
    assert row.exemption_end_date is None


def test_dates_are_never_guessed():
    rows = {r.name: r for r in parse(BODY)}
    # One-digit day: unambiguous, so it is read.
    assert rows["Comanche AIDC"].effective_date == dt.date(2026, 11, 5)
    # A missing slash: kept as the state typed it, with no parsed date.
    odd = rows["Lancium Abilene Clean Campus IX"]
    assert (odd.effective_date, odd.effective_date_text) == (None, "06/172026")
    unread = [r for r in rows.values() if r.effective_date is None]
    assert len(unread) == 2
    ended = [r for r in rows.values() if r.exemption_end_date is not None]
    assert len(ended) == sum(bool(r.exemption_end_date_text) for r in rows.values())


@pytest.mark.parametrize(
    "old,new",
    [
        (b'<th scope="col">Owner Name</th>', b'<th scope="col">County</th>'),
        (b"Registered Qualifying Large Data Center Projects", b"Another list"),
        (b"<table", b"<div"),
    ],
)
def test_a_changed_layout_stops_the_parser(old, new):
    assert old in BODY
    with pytest.raises(LayoutChanged):
        parse(BODY.replace(old, new))


# --- end to end ---------------------------------------------------------------------------------


def run(tmp_path, sink, robots=ROBOTS):
    clock = FakeClock()
    web = Site(
        {URL: httpx.Response(200, content=BODY, headers={"Content-Type": META["content_type"]})},
        robots=robots,
    )
    src = source()
    with Fetcher(
        src, contact=CONTACT, transport=web.transport, clock=clock, sleep=clock.sleep
    ) as fetcher:
        summary = ComptrollerDataCenters().run(
            source=src, fetcher=fetcher, store=LocalArchive(tmp_path), sink=sink, runner="test"
        )
    return summary, web


def test_the_source_is_cleared_for_the_fetcher():
    src = source()
    assert str(src.url) == URL == META["url"]
    assert src.may_fetch_automatically
    assert (FIXTURES.parents[2] / "docs" / "sources" / f"{src.id}.md").exists()


def test_the_page_is_archived_end_to_end(tmp_path):
    sink = MemorySink()
    summary, web = run(tmp_path, sink)

    assert (summary.status, summary.documents_seen, summary.documents_new, summary.errors) == (
        "ok", 1, 1, 0,
    )  # fmt: skip
    assert web.page_urls() == [URL]
    (doc,) = sink.documents.values()
    # Traceability: the URL, the retrieval time, the hash and the original bytes.
    assert doc.url == URL
    assert doc.sha256 == META["sha256"]
    assert doc.retrieved_at.tzinfo is not None
    stored = LocalArchive(tmp_path).get(doc.storage_path)
    assert stored == BODY
    assert "Registered Qualifying Large Data Center Projects" in doc.text
    assert "Whinstone US Data Center" in doc.text
    # The archived bytes parse to the same rows as the fixture.
    assert parse(stored) == parse(BODY)

    again, _ = run(tmp_path, sink)
    assert (again.status, again.documents_seen, again.documents_new) == ("ok", 1, 0)


def test_the_run_stops_if_robots_closes_the_folder(tmp_path):
    sink = MemorySink()
    summary, web = run(tmp_path, sink, robots="User-agent: *\nDisallow: /*/\n")
    assert summary.status == "blocked"
    assert web.page_urls() == []
    assert sink.documents == {}
