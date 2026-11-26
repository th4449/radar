"""Rules for the list of study payers, enforced in the database. Written before the migration.

See BUILD_PLAN.md milestone M12. The radar keeps the payers named in the QPQ Tracker's data
center study and notes which companies on record have the same name as one.

  Who reads       approved reviewers and administrators. Not the anonymous key.
  Who writes      the pipeline alone. No one through the app.
  The public      a published alert gives the payer's name as the study writes it and the
                  address of its page in the study. Never the name a record gave.
"""

from __future__ import annotations

import uuid

import psycopg
import pytest

from .conftest import as_anon, as_service, as_user, confirm, make_reviewer, make_site, refused

pytestmark = pytest.mark.db

# Two payer pages that no stored record can hold. A payer's page is unique in the table. These
# were two real pages of the study until November 26, 2026, when the hosted database held the
# real payers and refused the tests' rows before any policy was asked.
PAGE = f"https://www.purchasingpolicy.org/entity/{uuid.uuid4()}"
OTHER = f"https://www.purchasingpolicy.org/entity/{uuid.uuid4()}"


def scalar(conn: psycopg.Connection, sql: str, params: list | None = None):
    return conn.execute(sql, params).fetchone()[0]


def make_study_document(conn: psycopg.Connection) -> int:
    source_id = scalar(
        conn,
        """insert into public.sources (slug, state, name, url, method, cadence)
           values (%s, 'US', 'Test study', 'https://www.purchasingpolicy.org/data-centers',
                   'manual', 'monthly')
           returning id""",
        [f"us_test_{uuid.uuid4().hex[:8]}"],
    )
    return scalar(
        conn,
        """insert into public.documents (source_id, url, retrieved_at, sha256, text)
           values (%s, 'https://www.purchasingpolicy.org/data-centers', now(), %s, 'All payers')
           returning id""",
        [source_id, uuid.uuid4().hex + uuid.uuid4().hex],
    )


def make_payer(conn, name="Example Electric", url=PAGE, states="{TX}") -> int:
    return scalar(
        conn,
        """insert into public.study_payers (document_id, name, payer_class, url, states)
           values (%s, %s, 'Utility', %s, %s) returning id""",
        [make_study_document(conn), name, url, states],
    )


def make_entity(conn, name="Example Electric Delivery Company LLC") -> int:
    return scalar(
        conn,
        """insert into public.entities (name, normalized_name, match_key, kind)
           values (%s, upper(%s), upper(%s), 'company') returning id""",
        [name, name, name],
    )


def match(conn, entity: int, payer: int, basis="same_name") -> None:
    conn.execute(
        """insert into public.entity_study_payers (entity_id, payer_id, basis, matched_name)
           values (%s, %s, %s, 'Example Electric')""",
        [entity, payer, basis],
    )


def site_naming(conn, entity: int, label="Tract with a named company") -> int:
    site = make_site(conn, label)
    conn.execute("update public.signals set entity_id = %s where site_id = %s", [entity, site])
    return site


def publish(conn, site: int) -> int:
    admin = make_reviewer(conn, role="admin")
    confirm(conn, admin, site)
    with as_user(conn, admin):
        return scalar(
            conn,
            """insert into public.alerts (site_id, headline, body, published_at)
               values (%s, 'Signals in Hood County', 'Body', now()) returning id""",
            [site],
        )


# --- who reads ----------------------------------------------------------------------------------


def test_an_approved_reviewer_reads_payers_and_matches(db):
    payer = make_payer(db)
    match(db, make_entity(db), payer)
    with as_user(db, make_reviewer(db)):
        assert scalar(db, "select count(*) from public.study_payers where id = %s", [payer]) == 1
        assert (
            scalar(
                db, "select count(*) from public.entity_study_payers where payer_id = %s", [payer]
            )
            == 1
        )


@pytest.mark.parametrize("status", ["pending", "suspended"])
def test_a_reviewer_who_is_not_approved_reads_neither(db, status):
    match(db, make_entity(db), make_payer(db))
    with as_user(db, make_reviewer(db, status=status)):
        assert scalar(db, "select count(*) from public.study_payers") == 0
        assert scalar(db, "select count(*) from public.entity_study_payers") == 0


@pytest.mark.parametrize("table", ["study_payers", "entity_study_payers"])
def test_the_anonymous_key_reads_neither_table(db, table):
    match(db, make_entity(db), make_payer(db))
    with as_anon(db), pytest.raises(psycopg.errors.InsufficientPrivilege), db.transaction():
        db.execute(f"select count(*) from public.{table}")


# --- who writes ---------------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["reviewer", "admin"])
def test_no_one_writes_payers_or_matches_through_the_app(db, role):
    payer = make_payer(db)
    entity = make_entity(db)
    other = make_entity(db, "Another Example LLC")
    match(db, entity, payer)
    document = make_study_document(db)
    with as_user(db, make_reviewer(db, role=role)):
        assert refused(db, "update public.study_payers set name = 'Edited'")
        assert refused(db, "delete from public.study_payers")
        assert refused(db, "delete from public.entity_study_payers")
        assert refused(db, "update public.entity_study_payers set basis = 'same_name'")
        with pytest.raises(psycopg.errors.InsufficientPrivilege), db.transaction():
            db.execute(
                """insert into public.study_payers (document_id, name, payer_class, url, states)
                   values (%s, 'Added', 'Utility', %s, '{MI}')""",
                [document, OTHER],
            )
        with pytest.raises(psycopg.errors.InsufficientPrivilege), db.transaction():
            db.execute(
                """insert into public.entity_study_payers
                     (entity_id, payer_id, basis, matched_name)
                   values (%s, %s, 'same_name', 'Example')""",
                [other, payer],
            )


def test_the_pipeline_writes_both(db):
    document = make_study_document(db)
    entity = make_entity(db)
    with as_service(db):
        payer = scalar(
            db,
            """insert into public.study_payers (document_id, name, payer_class, url, states)
               values (%s, 'Example Electric', 'Utility', %s, '{TX,MI}') returning id""",
            [document, PAGE],
        )
        match(db, entity, payer, basis="same_name_legal_form_aside")
        assert (
            scalar(
                db, "select count(*) from public.entity_study_payers where payer_id = %s", [payer]
            )
            == 1
        )


# --- what a row may hold ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://example.org/entity/139640b7-37f0-4bea-a87a-ab0d38580032",
        "http://www.purchasingpolicy.org/entity/139640b7-37f0-4bea-a87a-ab0d38580032",
        "https://www.purchasingpolicy.org/entity/oncor",
        "javascript:alert(1)",
    ],
)
def test_a_payers_address_is_always_its_page_in_the_study(db, url):
    with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
        make_payer(db, url=url)


def test_a_payer_is_listed_once(db):
    make_payer(db)
    with pytest.raises(psycopg.errors.UniqueViolation), db.transaction():
        make_payer(db, name="The same page under another name")
    with pytest.raises(psycopg.errors.UniqueViolation), db.transaction():
        make_payer(db, url=OTHER)


def test_a_payer_names_the_copy_of_the_page_it_was_read_from(db):
    with pytest.raises(psycopg.errors.NotNullViolation), db.transaction():
        db.execute(
            """insert into public.study_payers (name, payer_class, url, states)
               values ('No copy', 'Utility', %s, '{TX}')""",
            [PAGE],
        )


def test_a_match_says_how_the_names_met(db):
    payer = make_payer(db)
    with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
        match(db, make_entity(db), payer, basis="looks_related")


def test_a_payer_that_leaves_the_study_takes_its_matches_with_it(db):
    payer = make_payer(db)
    match(db, make_entity(db), payer)
    db.execute("delete from public.study_payers where id = %s", [payer])
    assert (
        scalar(db, "select count(*) from public.entity_study_payers where payer_id = %s", [payer])
        == 0
    )


# --- what the public sees -----------------------------------------------------------------------


def test_a_public_alert_gives_the_payer_as_the_study_writes_it(db):
    entity = make_entity(db)
    match(db, entity, make_payer(db))
    alert = publish(db, site_naming(db, entity))
    with as_anon(db):
        payers = scalar(
            db, "select study_payers from public.public_alerts where alert_id = %s", [alert]
        )
    assert payers == [{"name": "Example Electric", "url": PAGE}]


def test_a_public_alert_never_gives_the_name_a_record_gave(db):
    entity = make_entity(db, "Example Electric Delivery Company LLC")
    match(db, entity, make_payer(db))
    alert = publish(db, site_naming(db, entity))
    with as_anon(db):
        row = db.execute(
            "select to_jsonb(a)::text from public.public_alerts a where alert_id = %s", [alert]
        ).fetchone()[0]
    assert "Delivery Company" not in row


def test_a_payer_is_given_once_however_many_records_name_it(db):
    entity = make_entity(db)
    match(db, entity, make_payer(db))
    site = site_naming(db, entity)
    db.execute(
        """insert into public.signals (document_id, signal_type, event_date, summary, site_id,
                                       entity_id, confidence)
           select document_id, signal_type, event_date, 'A second record', site_id, entity_id, 0.9
           from public.signals where site_id = %s""",
        [site],
    )
    alert = publish(db, site)
    with as_anon(db):
        payers = scalar(
            db, "select study_payers from public.public_alerts where alert_id = %s", [alert]
        )
    assert len(payers) == 1


def test_an_alert_with_no_match_gives_an_empty_list(db):
    make_payer(db)
    alert = publish(db, site_naming(db, make_entity(db, "Unrelated Works LLC")))
    with as_anon(db):
        assert (
            scalar(db, "select study_payers from public.public_alerts where alert_id = %s", [alert])
            == []
        )


def test_a_match_at_a_site_that_is_not_published_stays_private(db):
    entity = make_entity(db)
    match(db, entity, make_payer(db))
    site = site_naming(db, entity)
    with as_anon(db):
        assert (
            scalar(db, "select count(*) from public.public_alerts where site_id = %s", [site]) == 0
        )
