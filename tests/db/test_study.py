"""The payers and the matches, rebuilt in the database from a stored copy of the study's page."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import psycopg
import pytest

from collectors.base import FetchResult, LocalArchive, archive
from collectors.us.qpq_data_center_payers import URL
from pipeline import process, study
from pipeline.config import load_sources
from pipeline.entities import canonical_name, match_key
from pipeline.store import PostgresSink

from .conftest import as_service

pytestmark = pytest.mark.db

PAGE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "us_qpq_data_center_payers"
    / "data-centers-payers.html"
).read_bytes()
SOURCE = load_sources().by_id(study.SOURCE_ID)
DAY = dt.datetime(2026, 11, 24, 12, 0, tzinfo=dt.UTC)


def scalar(conn: psycopg.Connection, sql: str, params: list | None = None):
    return conn.execute(sql, params).fetchone()[0]


class Stored:
    def __init__(self, conn: psycopg.Connection, root: Path) -> None:
        self.conn, self.store, self.sink = conn, LocalArchive(root), PostgresSink(conn)

    def add_page(self, body: bytes = PAGE, day: int = 0) -> int:
        when = DAY + dt.timedelta(days=day)
        result = FetchResult(URL, URL, 200, "text/html", None, None, body, when)
        with as_service(self.conn):
            self.sink.start_run(SOURCE)
            doc = archive(result, SOURCE, self.store)
            assert self.sink.save_document(doc)
        return scalar(self.conn, "select id from public.documents where sha256 = %s", [doc.sha256])

    def add_company(self, name: str) -> int:
        return scalar(
            self.conn,
            """insert into public.entities (name, normalized_name, match_key, kind)
               values (%s, %s, %s, 'company') returning id""",
            [name, canonical_name(name), match_key(name)],
        )

    def update(self) -> dict:
        with as_service(self.conn):
            return study.update(self.conn, self.store)

    def matches(self) -> list[tuple[str, str, str, str]]:
        return self.conn.execute(
            """select e.name, p.name, m.basis, m.matched_name
               from public.entity_study_payers m
               join public.entities e on e.id = m.entity_id
               join public.study_payers p on p.id = m.payer_id
               order by e.name"""
        ).fetchall()


@pytest.fixture
def stored(db, tmp_path) -> Stored:
    return Stored(db, tmp_path)


def test_with_no_copy_of_the_page_nothing_is_written(stored):
    stored.add_company("Oncor Electric Delivery Company LLC")
    assert stored.update() == {"note": "No copy of the study's list of payers is stored."}
    assert scalar(stored.conn, "select count(*) from public.study_payers") == 0


def test_the_payers_and_the_matches_are_written_from_the_stored_copy(stored):
    document = stored.add_page()
    stored.add_company("Oncor Electric Delivery Company LLC")
    stored.add_company("Google")
    stored.add_company("Example Data LLC")
    stored.add_company("Google Fiber Texas LLC")

    assert stored.update() == {
        "document_id": document,
        "read_on": "2026-11-24",
        "payers": 61,
        "companies_matched": 2,
    }
    assert stored.matches() == [
        ("Google", "Google", "same_name", "Google"),
        (
            "Oncor Electric Delivery Company LLC",
            "Oncor",
            "same_name_legal_form_aside",
            "Oncor Electric Delivery",
        ),
    ]
    # Every payer names the copy it was read from, and keeps the study's own words.
    assert stored.conn.execute(
        """select payer_class, states, url, document_id from public.study_payers
           where name = 'Oncor'"""
    ).fetchone() == (
        "Utility",
        ["TX"],
        "https://www.purchasingpolicy.org/entity/139640b7-37f0-4bea-a87a-ab0d38580032",
        document,
    )


def test_a_second_run_writes_the_same_thing_and_picks_up_a_new_company(stored):
    stored.add_page()
    stored.add_company("Google")
    stored.update()
    stored.add_company("DTE Energy Company")
    assert stored.update()["companies_matched"] == 2
    assert scalar(stored.conn, "select count(*) from public.study_payers") == 61
    assert [m[0] for m in stored.matches()] == ["DTE Energy Company", "Google"]


def test_a_payer_the_study_drops_goes_with_its_match(stored):
    stored.add_page()
    stored.add_company("Walbridge")
    stored.update()
    assert [m[1] for m in stored.matches()] == ["Walbridge"]

    start = PAGE.rindex(b"<tr")
    end = PAGE.index(b"</tr>", start) + len(b"</tr>")
    assert b"Walbridge" in PAGE[start:end]
    shorter = (PAGE[:start] + PAGE[end:]).replace(b"<!-- -->61<!-- -->", b"<!-- -->60<!-- -->")
    stored.add_page(shorter, day=30)
    assert stored.update()["payers"] == 60
    assert stored.matches() == []


def test_a_copy_that_cannot_be_read_leaves_the_list_as_it_was(stored):
    stored.add_page()
    stored.add_company("Google")
    stored.update()
    odd = stored.add_page(PAGE.replace(b">Direct giving</th>", b">Total</th>"), day=30)

    out = stored.update()
    assert out == {"error": f"document {odd}: expected one table of payers, found 0"}
    assert scalar(stored.conn, "select count(*) from public.study_payers") == 61
    assert len(stored.matches()) == 1


def test_a_processing_run_rebuilds_the_matches_and_logs_them(stored):
    stored.add_page()
    stored.add_company("Consumers Energy Company")
    with as_service(stored.conn):
        summary = process.run(stored.conn, stored.store)
    assert summary.status == "ok"
    assert summary.detail["study"]["payers"] == 61
    assert summary.detail["study"]["companies_matched"] == 1
    assert stored.matches() == [
        (
            "Consumers Energy Company",
            "CMS / Consumers Energy",
            "same_name_legal_form_aside",
            "Consumers Energy",
        )
    ]


def test_a_processing_run_with_no_copy_still_ends_well(stored):
    with as_service(stored.conn):
        summary = process.run(stored.conn, stored.store)
    assert summary.status == "ok"
    assert "note" in summary.detail["study"]
