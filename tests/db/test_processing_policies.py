"""Rules for what processing stores, enforced in the database. Written before the migration.

A list of permit applicants or well owners names people. Such a document is restricted: only
an administrator reads it. A reviewer reads the signal made from one of its rows, which the
pipeline wrote only after checking that the row names a company or a public body.
"""

from __future__ import annotations

import datetime as dt
import uuid

import psycopg
import pytest

from collectors.base import ArchivedDocument
from pipeline.store import PostgresSink

from ..helpers import make_source
from .conftest import as_anon, as_service, as_user, make_reviewer, make_user, refused

pytestmark = pytest.mark.db


def make_document(conn: psycopg.Connection, *, restricted: bool) -> int:
    source_id = conn.execute(
        """insert into public.sources (slug, state, name, url, method, cadence)
           values (%s, 'TX', 'Test list', 'https://example.gov/list', 'manual', 'weekly')
           returning id""",
        [f"tx_test_{uuid.uuid4().hex[:8]}"],
    ).fetchone()[0]
    return conn.execute(
        """insert into public.documents (source_id, url, retrieved_at, sha256, text, restricted)
           values (%s, 'https://example.gov/list', now(), %s, 'INVENTED PERSON|Hood', %s)
           returning id""",
        [source_id, uuid.uuid4().hex + uuid.uuid4().hex, restricted],
    ).fetchone()[0]


def visible(conn: psycopg.Connection, doc_id: int) -> bool:
    return conn.execute("select 1 from public.documents where id = %s", [doc_id]).fetchone() == (1,)


def test_documents_are_open_unless_marked(db):
    doc_id = make_document(db, restricted=False)
    assert db.execute(
        "select restricted from public.documents where id = %s", [doc_id]
    ).fetchone() == (False,)


def test_a_reviewer_cannot_read_a_restricted_document(db):
    open_doc = make_document(db, restricted=False)
    held_doc = make_document(db, restricted=True)
    reviewer = make_reviewer(db)
    with as_user(db, reviewer):
        assert visible(db, open_doc)
        assert not visible(db, held_doc)


def test_an_administrator_reads_a_restricted_document(db):
    held_doc = make_document(db, restricted=True)
    admin = make_reviewer(db, role="admin")
    with as_user(db, admin):
        assert visible(db, held_doc)


@pytest.mark.parametrize("status", ["pending", "suspended"])
def test_a_reviewer_who_is_not_approved_reads_no_document(db, status):
    open_doc = make_document(db, restricted=False)
    held_doc = make_document(db, restricted=True)
    person = make_reviewer(db, status=status)
    with as_user(db, person):
        assert not visible(db, open_doc)
        assert not visible(db, held_doc)


def test_a_suspended_administrator_reads_no_restricted_document(db):
    held_doc = make_document(db, restricted=True)
    admin = make_reviewer(db, status="suspended", role="admin")
    with as_user(db, admin):
        assert not visible(db, held_doc)


def test_a_subscriber_and_the_anonymous_key_read_no_document(db):
    held_doc = make_document(db, restricted=True)
    with as_user(db, make_user(db)):
        assert not visible(db, held_doc)
    with as_anon(db), pytest.raises(psycopg.errors.InsufficientPrivilege), db.transaction():
        visible(db, held_doc)


@pytest.mark.parametrize("who", ["reviewer", "admin"])
def test_nobody_can_open_a_restricted_document_through_the_app(db, who):
    held_doc = make_document(db, restricted=True)
    actor = make_reviewer(db, role="admin" if who == "admin" else "reviewer")
    with as_user(db, actor):
        assert refused(
            db, "update public.documents set restricted = false where id = %s", [held_doc]
        )


def test_a_reviewer_reads_the_signal_made_from_a_restricted_document(db):
    held_doc = make_document(db, restricted=True)
    db.execute(
        """insert into public.signals (document_id, signal_type, event_date, summary, fingerprint,
                                       county_fips, extracted)
           values (%s, 'well_report', current_date, 'Well report 1: Example Data LLC', %s, '48221',
                   '{"row": {"OwnerName": "Example Data LLC"}}'::jsonb)""",
        [held_doc, "a" * 64],
    )
    reviewer = make_reviewer(db)
    with as_user(db, reviewer):
        rows = db.execute(
            "select summary, county_fips, extracted->'row'->>'OwnerName' from public.signals"
            " where document_id = %s",
            [held_doc],
        ).fetchall()
        assert rows == [("Well report 1: Example Data LLC", "48221", "Example Data LLC")]
        assert not visible(db, held_doc)


def test_the_same_fact_is_stored_once(db):
    doc_id = make_document(db, restricted=False)
    insert = """insert into public.signals (document_id, signal_type, event_date, summary,
                                            fingerprint)
                values (%s, 'air_permit', current_date, 'x', %s)
                on conflict (fingerprint) do nothing"""
    assert db.execute(insert, [doc_id, "b" * 64]).rowcount == 1
    assert db.execute(insert, [doc_id, "b" * 64]).rowcount == 0


def test_an_entity_is_a_company_or_a_public_body_and_nothing_else(db):
    db.execute(
        """insert into public.entities (name, normalized_name, match_key, kind)
           values ('Example Data, LLC', 'EXAMPLE DATA LLC', 'EXAMPLE DATA', 'company')"""
    )
    for kind in ("unclear", "person"):
        with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
            db.execute(
                "insert into public.entities (name, normalized_name, match_key, kind)"
                " values ('x', %s, 'X', %s)",
                [f"X {kind}", kind],
            )
    with pytest.raises(psycopg.errors.NotNullViolation), db.transaction():
        db.execute("insert into public.entities (name, normalized_name) values ('y', 'Y')")
    with pytest.raises(psycopg.errors.UniqueViolation), db.transaction():
        db.execute(
            """insert into public.entities (name, normalized_name, match_key, kind)
               values ('EXAMPLE DATA LLC', 'EXAMPLE DATA LLC', 'EXAMPLE DATA', 'company')"""
        )


def test_the_collector_marks_documents_from_a_list_that_names_people(db):
    def doc(source_id: str, sha: str) -> ArchivedDocument:
        return ArchivedDocument(
            source_id, "https://records.example.gov/list",
            dt.datetime(2026, 11, 20, 12, 0, tzinfo=dt.UTC), sha, f"{sha[:2]}/{sha}.txt", "rows",
            {},
        )  # fmt: skip

    listed = make_source(id="tx_example_list", personal_rows=True)
    plain = make_source(id="tx_example_plain")
    with as_service(db):
        sink = PostgresSink(db)
        sink.start_run(listed)
        sink.start_run(plain)
        sink.save_document(doc("tx_example_list", "c" * 64))
        sink.save_document(doc("tx_example_plain", "d" * 64))
    rows = dict(
        db.execute(
            """select s.slug, d.restricted from public.documents d
               join public.sources s on s.id = d.source_id
               where s.slug in ('tx_example_list', 'tx_example_plain')"""
        ).fetchall()
    )
    assert rows == {"tx_example_list": True, "tx_example_plain": False}


def test_processing_runs_are_for_administrators(db):
    db.execute("insert into public.processing_runs (rules_version) values ('test')")
    admin, reviewer = make_reviewer(db, role="admin"), make_reviewer(db)
    with as_user(db, admin):
        assert db.execute("select count(*) from public.processing_runs").fetchone()[0] >= 1
    with as_user(db, reviewer):
        assert db.execute("select count(*) from public.processing_runs").fetchone() == (0,)
        assert refused(db, "insert into public.processing_runs (rules_version) values ('x')")
    with as_anon(db), pytest.raises(psycopg.errors.InsufficientPrivilege), db.transaction():
        db.execute("select * from public.processing_runs")
