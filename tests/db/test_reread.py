"""The pages with no words, noted on PDFs that were stored before the note was kept."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import psycopg
import pytest

from collectors.base import FetchResult, LocalArchive, archive
from pipeline import reread
from pipeline.config import load_sources
from pipeline.signals import Doc, Rules, agenda_file, read_listings
from pipeline.store import PostgresSink

from ..helpers import make_pdf
from .conftest import as_service

pytestmark = pytest.mark.db

SOURCE = load_sources().by_id("tx_agendas_own_sites")
WHEN = dt.datetime(2026, 11, 23, 12, 0, tzinfo=dt.UTC)
TODAY = dt.date(2026, 11, 25)
LIST = (
    Path(__file__).parent.parent
    / "fixtures"
    / "tx_comptroller_data_centers"
    / "data-center-lists.html"
).read_bytes()
RULES = Rules(listings=read_listings(LIST), listings_sha256=hashlib.sha256(LIST).hexdigest())

HEAD = "CITY OF EXAMPLE\nNOTICE OF MEETING AND AGENDA\nTuesday, November 17, 2026 at 6:00 p.m."
ROUTINE = "1. Call to order.\n2. Approve the minutes of the last meeting.\n3. Pay the bills."
BILLS = "Bills for approval\nExample Electric, service to the data center site, 1,200.00"
FACTS = {
    "record": "agenda_file",
    "government": "Sealy city",
    "counties": ["Austin"],
    "bodies": ["Sealy City Council"],
    "page": "https://www.example.gov/government/agendas",
    "meeting_date": "2026-11-17",
    "date_from": "link_text",
}


class Stored:
    def __init__(self, conn: psycopg.Connection, root: Path) -> None:
        self.conn, self.root = conn, root
        self.store, self.sink = LocalArchive(root), PostgresSink(conn)
        self.count = 0

    def add(self, pages: list[str], note: bool = False, signal: bool = False) -> int:
        """One agenda file as it was stored before November 24, 2026: with no note."""
        self.count += 1
        url = f"https://www.example.gov/files/agenda-{self.count}.pdf"
        result = FetchResult(url, url, 200, "application/pdf", None, None, make_pdf(pages), WHEN)
        with as_service(self.conn):
            self.sink.start_run(SOURCE)
            doc = archive(result, SOURCE, self.store, FACTS)
            assert self.sink.save_document(doc)
            document_id = self.conn.execute(
                "select id from public.documents where sha256 = %s", [doc.sha256]
            ).fetchone()[0]
            if not note:
                self.conn.execute(
                    "update public.documents set raw_meta = raw_meta - %s where id = %s",
                    [reread.NOTE, document_id],
                )
            if signal:
                meta = self.meta(document_id)
                (draft,) = agenda_file(
                    Doc(SOURCE.id, url, WHEN, doc.sha256, doc.text, meta, b""), RULES
                ).drafts
                self.conn.execute(
                    """insert into public.signals
                         (document_id, signal_type, event_date, summary, confidence, extracted,
                          fingerprint, county_fips)
                       values (%s, %s, %s, %s, %s, %s::jsonb, %s, %s)""",
                    [document_id, draft.signal_type, draft.event_date, draft.summary,
                     draft.confidence, json.dumps(draft.extracted),
                     hashlib.sha256(url.encode()).hexdigest(), draft.county_fips],
                )  # fmt: skip
        return document_id

    def meta(self, document_id: int) -> dict:
        return self.conn.execute(
            "select raw_meta from public.documents where id = %s", [document_id]
        ).fetchone()[0]

    def text(self, document_id: int) -> str:
        return self.conn.execute(
            "select text from public.documents where id = %s", [document_id]
        ).fetchone()[0]

    def signal(self, document_id: int) -> tuple[str, dict]:
        return self.conn.execute(
            "select summary, extracted from public.signals where document_id = %s", [document_id]
        ).fetchone()

    def run(self, write: bool = True, **kwargs) -> reread.RereadSummary:
        with as_service(self.conn):
            return reread.reread(self.conn, self.store, write=write, today=TODAY, **kwargs)


@pytest.fixture
def stored(db, tmp_path) -> Stored:
    return Stored(db, tmp_path)


def test_a_file_with_words_on_every_page_gets_an_empty_note_and_is_not_opened(stored):
    document_id = stored.add([HEAD, ROUTINE, BILLS])
    for path in stored.root.rglob("*.pdf"):
        path.unlink()  # the file is gone, and the job does not need it
    summary = stored.run()
    assert (summary.documents, summary.noted_unopened, summary.read_again) == (1, 1, 0)
    meta = stored.meta(document_id)
    assert meta["pages_without_text"] == []
    assert meta["pages_noted"] == {"on": "2026-11-25", "file_read_again": False}


def test_a_file_with_a_page_without_words_is_read_again_and_its_pages_noted(stored):
    document_id = stored.add(["", HEAD, "", ROUTINE, BILLS])
    before = stored.text(document_id)
    summary = stored.run()
    assert (summary.read_again, summary.noted_after_reading) == (1, 1)
    assert summary.with_a_page_without_words == 1 and summary.left == {}
    meta = stored.meta(document_id)
    assert meta["pages_without_text"] == [1, 3] and meta["pages"] == 5
    assert meta["pages_noted"] == {"on": "2026-11-25", "file_read_again": True}
    assert stored.text(document_id) == before  # no stored text changes
    # What the archive step would have noted, had the file been stored today.
    assert stored.meta(stored.add(["", HEAD, "", ROUTINE, "Other bills"], note=True))[
        "pages_without_text"
    ] == [1, 3]


def test_a_signal_made_before_the_note_is_given_the_files_own_page_numbers(stored):
    document_id = stored.add(["", HEAD, "", ROUTINE, BILLS], signal=True)
    summary_before, before = stored.signal(document_id)
    # Counted over the text: the third piece. The file's own page is the fifth.
    assert (before["pages_with_terms"], before["pages_exact"]) == ([3], False)

    summary = stored.run()
    assert (summary.signals_checked, summary.signals_changed) == (1, 1)
    summary_after, after = stored.signal(document_id)
    assert (after["pages_with_terms"], after["pages_exact"]) == ([5], True)
    assert after["pages_renumbered"] == {"on": "2026-11-25", "from": [3]}
    # Nothing else about the signal changes.
    assert summary_after == summary_before
    kept = {k: v for k, v in after.items() if k not in ("pages_with_terms", "pages_exact")}
    kept.pop("pages_renumbered")
    assert kept == {k: v for k, v in before.items() if k not in ("pages_with_terms", "pages_exact")}
    # The same numbers a fresh read of the noted file gives.
    meta = stored.meta(document_id)
    (fresh,) = agenda_file(
        Doc(SOURCE.id, "u", WHEN, "x", stored.text(document_id), meta, b""), RULES
    ).drafts
    assert fresh.extracted["pages_with_terms"] == after["pages_with_terms"]


def test_a_signal_whose_numbers_were_right_is_marked_sure_and_not_marked_changed(stored):
    document_id = stored.add([HEAD, ROUTINE, BILLS], signal=True)
    summary = stored.run()
    assert (summary.signals_checked, summary.signals_changed) == (1, 0)
    _, after = stored.signal(document_id)
    assert (after["pages_with_terms"], after["pages_exact"]) == ([3], True)
    assert "pages_renumbered" not in after


def test_without_write_nothing_is_written_and_the_count_is_the_same(stored):
    document_id = stored.add(["", HEAD, ROUTINE, BILLS], signal=True)
    summary = stored.run(write=False)
    assert summary.wrote is False
    assert (summary.documents, summary.noted_after_reading, summary.signals_changed) == (1, 1, 1)
    assert "pages_without_text" not in stored.meta(document_id)
    assert stored.signal(document_id)[1]["pages_exact"] is False


def test_a_second_run_finds_nothing_to_do(stored):
    document_id = stored.add(["", HEAD, ROUTINE, BILLS], signal=True)
    stored.run()
    first = stored.signal(document_id)
    again = stored.run()
    assert (again.documents, again.signals_checked) == (0, 0)
    assert stored.signal(document_id) == first


def test_a_file_already_noted_is_left_alone(stored):
    document_id = stored.add(["", HEAD, ROUTINE], note=True)
    assert stored.run().documents == 0
    assert "pages_noted" not in stored.meta(document_id)


def test_a_file_that_reads_differently_today_is_left_and_counted(stored):
    document_id = stored.add(["", HEAD, ROUTINE, BILLS])
    with as_service(stored.conn):
        stored.conn.execute(
            "update public.documents set text = replace(text, 'Pay the bills', 'Pay bills') "
            "where id = %s",
            [document_id],
        )
    summary = stored.run()
    assert summary.left == {reread.TEXT_DIFFERS: 1}
    assert summary.left_documents == {reread.TEXT_DIFFERS: [document_id]}
    assert "pages_without_text" not in stored.meta(document_id)


def test_a_file_missing_from_the_archive_or_not_the_one_stored_is_left(stored):
    missing = stored.add(["", HEAD, ROUTINE, BILLS])
    for path in stored.root.rglob("*.pdf"):
        path.unlink()
    other = stored.add(["", HEAD, ROUTINE, "Other bills"])
    (path,) = stored.root.rglob("*.pdf")
    path.write_bytes(make_pdf(["", HEAD, ROUTINE, "Changed"]))
    summary = stored.run()
    assert summary.left == {reread.NOT_IN_ARCHIVE: 1, reread.WRONG_FILE: 1}
    assert summary.left_documents[reread.NOT_IN_ARCHIVE] == [missing]
    assert summary.left_documents[reread.WRONG_FILE] == [other]


def test_a_scan_that_was_never_read_and_a_page_of_a_website_get_no_note(stored):
    scan = stored.add(["", ""])
    with as_service(stored.conn):
        stored.conn.execute("update public.documents set text = '' where id = %s", [scan])
    summary = stored.run()
    assert summary.left == {reread.NO_TEXT: 1}
    assert "pages_without_text" not in stored.meta(scan)


def test_only_one_sources_files_are_read_when_a_source_is_named(stored):
    document_id = stored.add([HEAD, ROUTINE])
    assert stored.run(source="tx_ercot_rpg").documents == 0
    assert "pages_without_text" not in stored.meta(document_id)
    assert stored.run(source=SOURCE.id).documents == 1


def test_the_old_numbers_are_piece_numbers_and_a_piece_of_an_attached_file_has_no_page():
    text = "\n\n".join([HEAD, ROUTINE, "File: exhibit.pdf\n" + BILLS])
    meta = {"pages": 4, "pages_without_text": [1, 3]}
    # Pieces one and two are pages 2 and 4. The third is the attached file's.
    assert reread.renumbered([1, 2, 3], meta, text) == [2, 4]
    assert reread.renumbered([], meta, text) == []
    assert reread.renumbered([7, "x", None, True], meta, text) == []
