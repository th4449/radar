"""The run log and document store in Postgres, written with the service role."""

from __future__ import annotations

import datetime as dt

import pytest

from collectors.base import ArchivedDocument, RunSummary
from pipeline.store import PostgresSink, sync_sources

from ..helpers import make_source
from .conftest import as_anon, as_service, as_user, make_reviewer, refused

pytestmark = pytest.mark.db


def a_document(sha: str = "a" * 64) -> ArchivedDocument:
    return ArchivedDocument(
        source_id="tx_example",
        url="https://records.example.gov/notices/1",
        retrieved_at=dt.datetime(2026, 11, 19, 12, 0, tzinfo=dt.UTC),
        sha256=sha,
        storage_path=f"{sha[:2]}/{sha}.html",
        text="Notice text",
        raw_meta={"kind": "html", "bytes": 11},
    )


def test_a_run_is_logged_and_documents_are_stored_once(db):
    source = make_source()
    with as_service(db):
        sink = PostgresSink(db)
        run_id = sink.start_run(source, runner="gha-123")
        assert sink.save_document(a_document()) is True
        assert sink.save_document(a_document()) is False  # same bytes, same source
        assert sink.save_document(a_document("b" * 64)) is True
        sink.finish_run(run_id, RunSummary("tx_example", "ok", 3, 2, 0, None, {}))

    row = db.execute(
        """select s.slug, r.status, r.documents_seen, r.documents_new, r.runner,
                  r.finished_at is not null
           from public.collector_runs r join public.sources s on s.id = r.source_id
           where r.id = %s""",
        [run_id],
    ).fetchone()
    assert row == ("tx_example", "ok", 3, 2, "gha-123", True)

    docs = db.execute(
        """select d.url, d.sha256, d.storage_path, d.text, d.raw_meta->>'kind', d.retrieved_at
           from public.documents d join public.sources s on s.id = d.source_id
           where s.slug = 'tx_example' order by d.sha256"""
    ).fetchall()
    assert len(docs) == 2
    assert docs[0][:5] == (
        "https://records.example.gov/notices/1", "a" * 64, f"aa/{'a' * 64}.html", "Notice text",
        "html",
    )  # fmt: skip
    assert docs[0][5] == dt.datetime(2026, 11, 19, 12, 0, tzinfo=dt.UTC)


def test_a_failed_run_keeps_its_error(db):
    with as_service(db):
        sink = PostgresSink(db)
        run_id = sink.start_run(make_source())
        sink.finish_run(
            run_id,
            RunSummary("tx_example", "blocked", 0, 0, 0, "HTTP 403 from records.example.gov", {}),
        )
    assert db.execute(
        "select status, error from public.collector_runs where id = %s", [run_id]
    ).fetchone() == ("blocked", "HTTP 403 from records.example.gov")


def test_sync_sources_updates_in_place(db):
    with as_service(db):
        first = sync_sources(db, [make_source(name="Old name")])
        second = sync_sources(db, [make_source(name="New name")])
    assert first == second
    assert db.execute(
        "select name, method, robots_status, verified_at::date from public.sources where slug = %s",
        ["tx_example"],
    ).fetchone() == ("New name", "http", "allowed", dt.date(2026, 11, 19))


def test_the_database_refuses_an_automated_source_that_was_not_verified(db):
    assert refused(
        db,
        """insert into public.sources (slug, state, name, url, method, cadence, robots_status)
           values ('tx_unverified', 'TX', 'x', 'https://example.gov', 'http', 'daily',
                   'not_checked')""",
    )


def test_only_admins_read_the_run_log(db):
    admin, reviewer = make_reviewer(db, role="admin"), make_reviewer(db)
    with as_service(db):
        PostgresSink(db).start_run(make_source())
    with as_user(db, reviewer):
        assert db.execute("select count(*) from public.collector_runs").fetchone()[0] == 0
        assert refused(db, "update public.collector_runs set status = 'ok'")
    with as_user(db, admin):
        assert db.execute("select count(*) from public.collector_runs").fetchone()[0] == 1
        assert refused(db, "update public.collector_runs set status = 'ok'")
    with as_anon(db):
        assert refused(db, "delete from public.collector_runs")
