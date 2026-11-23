"""The TWDB well report collector, run against a hand-built sample of the board's table.

The board's file is 145 MB and about four reports in ten name a household, so no copy of it is
in this repository. The sample has the board's header line, six real reports owned by
companies or a city with the driller and the owner's address removed, and nine invented rows.
Its .meta.json says which is which. The tests zip the sample the way the board does. No test
here touches the network.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import httpx
import pytest

from collectors.base import Fetcher, LayoutChanged, LocalArchive, TooLarge
from collectors.tx.twdb_well_reports import (
    COLUMNS,
    KEEP,
    TABLE,
    URL,
    TwdbWellReports,
    reduce_table,
    reduce_zip,
)
from pipeline.config import load_counties, load_sources
from pipeline.store import MemorySink

from .helpers import CONTACT, FakeClock, Site, make_zip

FIXTURES = Path(__file__).parent / "fixtures" / "tx_twdb_well_reports"
SAMPLE = (FIXTURES / "welldata-sample.txt").read_bytes()
META = json.loads((FIXTURES / "welldata-sample.meta.json").read_text())

TODAY = dt.date(2026, 11, 20)
SINCE = dt.date(2024, 11, 20)  # 730 days before
COUNTIES = frozenset(c.name for c in load_counties("TX").counties)
KEPT = ["9000008", "728122", "731019", "731020", "9000004", "9000005"]  # oldest first

# TWDB's robots file closes only its calendar, as read on November 19, 2026.
ROBOTS = "User-agent: *\nDisallow: /calendar/\n"


def board_zip(table: bytes = SAMPLE) -> bytes:
    return make_zip({"SDRDownload/ReadMe/ReadMe.txt": b"How to import.", TABLE: table})


def lines(table: bytes = SAMPLE) -> list[str]:
    return table.decode("cp1252").split("\r\n")


def source():
    return load_sources().by_id("tx_twdb_well_reports")


# --- the sample ---------------------------------------------------------------------------------


def test_the_sample_is_what_its_notes_say():
    assert hashlib.sha256(SAMPLE).hexdigest() == META["fixture_sha256"]
    assert META["url"] == URL
    header, *rows = [line.split("|") for line in lines() if line]
    assert tuple(header) == COLUMNS
    at = {name: i for i, name in enumerate(COLUMNS)}
    for row in rows:
        # No driller is named, and no real mailing address is present.
        assert row[at["DrillerName"]] == row[at["DrillerSigned"]] == row[at["LicenseNumber"]] == ""
        assert row[at["OwnerAddress1"]] in ("100 EXAMPLE ST", "1 INVENTED LANE")
        invented = row[0].startswith("9000")
        assert invented == row[at["OwnerName"]].startswith("INVENTED")


# --- which rows are kept ------------------------------------------------------------------------


def test_only_rows_the_radar_may_hold_are_kept():
    out = reduce_table(lines(), COUNTIES, SINCE)
    assert [row[0] for row in sorted(out.rows, key=lambda r: (r[1], r[0]))] == KEPT
    assert out.counts() == {
        "since": "2024-11-20",
        "rows_total": 15,
        "rows_kept": 6,
        "rows_other_county": 3,
        "rows_household": 2,
        "rows_too_old": 2,
        "rows_undated": 1,
        "rows_malformed": 1,
        "malformed_tracking_numbers": ["9000006"],
    }


def test_household_wells_are_never_kept():
    body = reduce_table(lines(), COUNTIES, SINCE).body().decode()
    assert "INVENTED HOUSEHOLD OWNER" not in body
    assert "INVENTED RANCH OWNER" not in body
    assert "|Domestic|" not in body and "|Stock|" not in body


def test_the_mailing_address_and_the_driller_are_left_out():
    body = reduce_table(lines(), COUNTIES, SINCE).body().decode()
    for dropped in ("100 EXAMPLE ST", "1 INVENTED LANE", "EXAMPLE CITY", "EXAMPLE DRILLING CO"):
        assert dropped.encode("cp1252") in SAMPLE
        assert dropped not in body
    for column in COLUMNS:
        if column.startswith(("OwnerAddress", "OwnerCity", "OwnerZip", "Driller", "Apprentice")):
            assert column not in KEEP
    assert "CompanyName" not in KEEP and "LicenseNumber" not in KEEP


def test_the_extract_is_one_header_and_one_line_per_row_oldest_first():
    text = reduce_table(lines(), COUNTIES, SINCE).body().decode("utf-8")
    header, *rows = text.splitlines()
    assert header.split("|") == list(KEEP)
    assert [row.split("|")[0] for row in rows] == KEPT
    cyrus = dict(zip(KEEP, rows[1].split("|"), strict=True))
    assert cyrus["OwnerName"] == "CyrusOne Bosque LLC"
    assert (cyrus["County"], cyrus["ProposedUse"]) == ("Bosque", "Public Supply")
    assert (cyrus["DateSubmitted"], cyrus["DrillingEndDate"]) == ("2026-07-16", "2026-06-04")
    assert (cyrus["WellAddress1"], cyrus["WellCity"]) == ("557 CR 3610", "Clifton")
    assert (cyrus["CoordDDLat"], cyrus["CoordDDLong"]) == ("31.849363", "-97.372186")


def test_a_comment_with_a_line_feed_and_windows_characters_stays_one_row():
    assert b"tests.\nSecond line, caf\xe9\xa0style." in SAMPLE
    text = reduce_table(lines(), COUNTIES, SINCE).body().decode("utf-8")
    row = next(line for line in text.splitlines() if line.startswith("9000004|"))
    assert row.endswith("|Invented row for tests. Second line, café style.|")


def test_a_county_with_two_words_matches():
    out = reduce_table(lines(), COUNTIES, SINCE)
    assert ("9000005", "Tom Green") in {(row[0], row[4]) for row in out.rows}


def test_the_two_year_window_includes_its_first_day():
    kept = {row[0] for row in reduce_table(lines(), COUNTIES, SINCE).rows}
    assert "9000008" in kept and "9000009" not in kept  # November 20 and 19, 2024
    later = {row[0] for row in reduce_table(lines(), COUNTIES, dt.date(2026, 9, 1)).rows}
    assert later == {"9000004", "9000005"}


# --- a changed file -----------------------------------------------------------------------------


def test_a_renamed_column_stops_the_run():
    changed = SAMPLE.replace(b"|ProposedUse|", b"|IntendedUse|", 1)
    with pytest.raises(LayoutChanged):
        reduce_table(lines(changed), COUNTIES, SINCE)


def test_a_zip_without_the_table_or_a_file_that_is_no_zip_stops_the_run():
    with pytest.raises(LayoutChanged, match="has no"):
        reduce_zip(make_zip({"SDRDownload/Other.txt": b"x"}), COUNTIES, SINCE)
    with pytest.raises(LayoutChanged, match="not a zip"):
        reduce_zip(b"<html>Sorry</html>", COUNTIES, SINCE)


# --- end to end ---------------------------------------------------------------------------------


def zip_route(body: bytes, etag: str = '"0726593e877dd1:0"'):
    def route(request: httpx.Request) -> httpx.Response:
        if request.headers.get("If-None-Match") == etag:
            return httpx.Response(304)
        headers = {"Content-Type": "application/x-zip-compressed", "ETag": etag}
        return httpx.Response(200, content=body, headers=headers)

    return route


def run(tmp_path, sink, web: Site, today: dt.date = TODAY):
    clock = FakeClock()
    src = source()
    with Fetcher(
        src, contact=CONTACT, transport=web.transport, clock=clock, sleep=clock.sleep
    ) as fetcher:
        summary = TwdbWellReports(today=today).run(
            source=src, fetcher=fetcher, store=LocalArchive(tmp_path), sink=sink, runner="test"
        )
    return summary


def test_the_source_is_cleared_and_its_size_limit_is_raised_in_config():
    src = source()
    assert src.may_fetch_automatically and src.cadence == "weekly"
    assert src.max_body_mb == 300
    assert [s.id for s in load_sources().sources if s.max_body_mb] == [src.id]
    assert (FIXTURES.parents[2] / "docs" / "sources" / f"{src.id}.md").exists()


def test_the_collector_uses_the_thirty_test_counties():
    assert TwdbWellReports(today=TODAY).counties == COUNTIES
    assert len(COUNTIES) == 30


def test_the_extract_is_stored_and_the_file_is_not(tmp_path):
    original = board_zip()
    sink, web = MemorySink(), Site({URL: zip_route(original)}, robots=ROBOTS)
    summary = run(tmp_path, sink, web)

    assert (summary.status, summary.documents_seen, summary.documents_new, summary.errors) == (
        "ok", 1, 1, 0,
    )  # fmt: skip
    assert web.page_urls() == [URL]
    (doc,) = sink.documents.values()
    stored = LocalArchive(tmp_path).get(doc.storage_path)

    # What is stored is the extract.
    assert doc.url == URL and doc.storage_path.endswith(".txt")
    assert stored.decode().splitlines()[0] == "|".join(KEEP)
    assert doc.sha256 == hashlib.sha256(stored).hexdigest()
    assert "CyrusOne Bosque LLC" in doc.text and "INVENTED HOUSEHOLD OWNER" not in doc.text

    # The board's file is recorded by address, time, size and hash, and is nowhere on disk.
    meta = doc.raw_meta
    assert meta["original_sha256"] == hashlib.sha256(original).hexdigest()
    assert (meta["original_bytes"], meta["original_kept"]) == (len(original), False)
    assert (meta["rows_total"], meta["rows_kept"], meta["rows_household"]) == (15, 6, 2)
    assert (meta["since"], meta["table"], meta["columns"]) == ("2024-11-20", TABLE, list(KEEP))
    assert meta["etag"] == '"0726593e877dd1:0"'
    assert doc.retrieved_at.tzinfo is not None
    on_disk = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert [p.read_bytes() for p in on_disk] == [stored]


def test_an_unchanged_file_costs_one_short_answer(tmp_path):
    sink = MemorySink()
    run(tmp_path, sink, Site({URL: zip_route(board_zip())}, robots=ROBOTS))

    web = Site({URL: zip_route(board_zip())}, robots=ROBOTS)
    again = run(tmp_path, sink, web)

    assert (again.status, again.documents_seen, again.documents_new) == ("ok", 1, 0)
    (request,) = [r for r in web.requests if r.url.path != "/robots.txt"]
    assert request.headers["If-None-Match"] == '"0726593e877dd1:0"'


def test_a_rebuild_that_changes_only_household_rows_is_not_stored_again(tmp_path):
    sink = MemorySink()
    run(tmp_path, sink, Site({URL: zip_route(board_zip())}, robots=ROBOTS))

    rebuilt = SAMPLE.replace(b"INVENTED HOUSEHOLD OWNER", b"INVENTED OTHER HOUSEHOLD")
    assert rebuilt != SAMPLE
    web = Site({URL: zip_route(board_zip(rebuilt), etag='"next-night"')}, robots=ROBOTS)
    again = run(tmp_path, sink, web)

    assert (again.status, again.documents_new) == ("ok", 0)
    assert len(sink.documents) == 1


def test_a_new_report_is_stored(tmp_path):
    sink = MemorySink()
    run(tmp_path, sink, Site({URL: zip_route(board_zip())}, robots=ROBOTS))

    newer = SAMPLE.replace(b"INVENTED COMPUTE CAMPUS LLC", b"INVENTED SECOND CAMPUS LLC")
    web = Site({URL: zip_route(board_zip(newer), etag='"next-night"')}, robots=ROBOTS)
    again = run(tmp_path, sink, web)

    assert (again.status, again.documents_new) == ("ok", 1)
    assert len(sink.documents) == 2


def test_a_changed_table_fails_the_run_and_keeps_nothing(tmp_path):
    changed = board_zip(SAMPLE.replace(b"|ProposedUse|", b"|IntendedUse|", 1))
    sink, web = MemorySink(), Site({URL: zip_route(changed)}, robots=ROBOTS)
    summary = run(tmp_path, sink, web)

    assert summary.status == "failed"
    assert "do not match" in summary.error
    # Other collectors keep the page that surprised them. This one must not: the file names
    # households. Only its size and hash are recorded.
    assert sink.documents == {}
    assert [p for p in tmp_path.rglob("*") if p.is_file()] == []
    assert summary.detail["unread_file"] == {
        "original_sha256": hashlib.sha256(changed).hexdigest(),
        "original_bytes": len(changed),
    }


def test_the_raised_limit_is_still_a_limit(tmp_path, monkeypatch):
    src = source().model_copy(update={"max_body_mb": None})
    monkeypatch.setattr("collectors.base.MAX_BODY_BYTES", 1000)
    web = Site({URL: zip_route(board_zip())}, robots=ROBOTS)
    clock = FakeClock()
    with (
        Fetcher(src, contact=CONTACT, transport=web.transport, clock=clock, sleep=clock.sleep) as f,
        pytest.raises(TooLarge),
    ):
        f.get(URL)


def test_the_run_stops_if_robots_closes_the_data_folder(tmp_path):
    web = Site({URL: zip_route(board_zip())}, robots=ROBOTS + "Disallow: /groundwater/\n")
    sink = MemorySink()
    summary = run(tmp_path, sink, web)
    assert summary.status == "blocked"
    assert web.page_urls() == [] and sink.documents == {}


# --- a one-time history run, for the backtest ----------------------------------------------------


def test_a_history_run_keeps_rows_since_its_first_day_and_adds_the_control_counties(tmp_path):
    from pipeline.config import load_control_counties

    history = TwdbWellReports.history(dt.date(2023, 1, 1), today=TODAY)
    controls = {c.name for c in load_control_counties("TX").counties}
    assert history.counties == COUNTIES | controls
    web = Site({URL: zip_route(board_zip())}, robots=ROBOTS)
    clock = FakeClock()
    src, sink = source(), MemorySink()
    with Fetcher(
        src, contact=CONTACT, transport=web.transport, clock=clock, sleep=clock.sleep
    ) as fetcher:
        history.run(source=src, fetcher=fetcher, store=LocalArchive(tmp_path), sink=sink)
    (doc,) = sink.documents.values()
    # 9000009 was submitted on November 19, 2024, a day outside the everyday two years.
    assert "9000009" in doc.text and "9000008" in doc.text


def test_an_everyday_run_keeps_its_two_years_and_its_thirty_counties():
    daily = TwdbWellReports(today=TODAY)
    assert daily.since == SINCE and daily.counties == COUNTIES
