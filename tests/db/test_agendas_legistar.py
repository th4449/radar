"""A Legistar agenda from the API to a signal in the database, end to end."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import httpx
import pytest

from collectors.base import Fetcher, LocalArchive
from collectors.tx.legistar import Client, LegistarAgendas, event_url, events_url
from pipeline import process
from pipeline.config import load_sources
from pipeline.store import PostgresSink

from ..helpers import CONTACT, FakeClock, Site
from .conftest import as_service, as_user, make_reviewer

pytestmark = pytest.mark.db

FIXTURES = Path(__file__).parent.parent / "fixtures" / "tx_agendas_legistar"
HARRIS_BODY = (FIXTURES / "harris-event-1244-trimmed.txt").read_bytes()
HARRIS = Client("harriscountytx", "Harris County", ("Harris",))
TODAY = dt.date(2026, 10, 16)
SOURCE = load_sources().by_id("tx_agendas_legistar")


def collect(conn, tmp_path) -> LocalArchive:
    meeting = json.loads(HARRIS_BODY)
    listed = {k: v for k, v in meeting.items() if k != "EventItems"}
    site = Site(
        {
            events_url("harriscountytx", dt.date(2026, 10, 2)): httpx.Response(200, json=[listed]),
            event_url("harriscountytx", 1244): httpx.Response(200, content=HARRIS_BODY),
        },
        robots=404,
    )
    store, clock = LocalArchive(tmp_path), FakeClock()
    with (
        as_service(conn),
        Fetcher(
            SOURCE, contact=CONTACT, transport=site.transport, clock=clock, sleep=clock.sleep
        ) as fetcher,
    ):
        summary = LegistarAgendas(clients=(HARRIS,), today=TODAY).run(
            source=SOURCE, fetcher=fetcher, store=store, sink=PostgresSink(conn)
        )
    assert summary.status == "ok", summary.error
    return store


def test_an_agenda_is_collected_stored_restricted_and_read_into_one_signal(db, tmp_path):
    store = collect(db, tmp_path)
    stored = db.execute(
        """select d.raw_meta ->> 'record', d.restricted from public.documents d
           join public.sources s on s.id = d.source_id
           where s.slug = 'tx_agendas_legistar' order by 1"""
    ).fetchall()
    # An agenda names people. Both documents are closed to reviewers from the moment they land.
    assert stored == [("legistar_agenda", True), ("legistar_meetings", True)]

    with as_service(db):
        summary = process.run(db, store, runner="test")
    assert summary.status == "ok", summary.error
    signals = db.execute(
        """select sg.signal_type, sg.county_fips, sg.event_date, sg.summary,
                  sg.extracted ->> 'reference', sg.entity_id
           from public.signals sg where sg.fingerprint is not null"""
    ).fetchall()
    assert signals == [
        (
            "agenda_keyword",
            "48201",
            dt.date(2026, 10, 15),
            "The agenda of the Harris County Commissioners Court for October 15, 2026 has an "
            'item that uses the words "data center": item 343, file 26-6897.',
            "Harris County Commissioners Court, meeting of October 15, 2026, item 343, "
            "file 26-6897",
            None,
        )
    ]


def test_a_reviewer_sees_the_signal_and_not_the_agendas_text(db, tmp_path):
    store = collect(db, tmp_path)
    with as_service(db):
        process.run(db, store, runner="test")
    reviewer = make_reviewer(db)
    with as_user(db, reviewer):
        assert db.execute("select count(*) from public.signals").fetchone()[0] == 1
        assert db.execute("select count(*) from public.documents").fetchone()[0] == 0
        refs = db.execute("select restricted, url from public.document_refs").fetchall()
    assert len(refs) == 2 and all(restricted for restricted, _ in refs)


def test_collecting_and_reading_again_adds_nothing(db, tmp_path):
    store = collect(db, tmp_path)
    with as_service(db):
        process.run(db, store, runner="test")
    collect(db, tmp_path)
    with as_service(db):
        again = process.run(db, store, runner="test")
    assert again.signals_new == 0
    assert db.execute("select count(*) from public.signals").fetchone()[0] == 1
    assert (
        db.execute(
            """select count(*) from public.documents d join public.sources s on s.id = d.source_id
               where s.slug = 'tx_agendas_legistar'"""
        ).fetchone()[0]
        == 2
    )
