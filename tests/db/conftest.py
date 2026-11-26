"""Fixtures for the policy tests.

The tests run against the local Supabase Postgres (`supabase db start`), because the policies
depend on Supabase's roles and on auth.uid(). Each test runs in one transaction that is rolled
back, so tests never see each other's rows.

A test acts as a user the same way the Supabase API does: it switches to the `authenticated`
role and sets the JWT claims for the request.

**Nothing a test writes is kept, whatever the test does.** The fixture opens the transaction
itself, before the test's first statement, so no block inside a test can be a transaction of its
own and commit.

**A database that is not on this machine is refused** unless RADAR_TEST_HOSTED is 1. That
switch is for the workflow that runs the policy tests on the hosted database, and even then
only the four policy files run. See docs/launch_checklist.md.

**RADAR_TEST_RESIDENTS=1 puts records in the database before each test,** inside the same
transaction: sites, a published alert, reviewers, a subscriber and a study payer. A policy test
must hold on a database that already holds records, as the hosted one does. CI runs the policy
tests both ways.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from urllib.parse import urlsplit

import psycopg
import pytest

DB_URL = os.environ.get(
    "RADAR_TEST_DB_URL", "postgresql://postgres:postgres@127.0.0.1:55322/postgres"
)
REQUIRE_DB = os.environ.get("RADAR_REQUIRE_DB") == "1"
HOSTED_ALLOWED = os.environ.get("RADAR_TEST_HOSTED") == "1"
RESIDENTS = os.environ.get("RADAR_TEST_RESIDENTS") == "1"
LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")
# The only files that may run on a database that is not on this machine. Each holds on a
# database with records in it. The other files here test the pipeline and assume empty tables.
HOSTED_FILES = frozenset(
    {
        "test_policies.py",
        "test_processing_policies.py",
        "test_site_policies.py",
        "test_study_policies.py",
    }
)


def is_local(url: str) -> bool:
    """True when the address names a database on this machine."""
    return (urlsplit(url).hostname or "") in LOCAL_HOSTS


pytestmark = pytest.mark.db


@pytest.fixture(scope="session")
def _db_available() -> None:
    if not is_local(DB_URL) and not HOSTED_ALLOWED:
        pytest.fail(
            "RADAR_TEST_DB_URL names a database that is not on this machine. These tests write "
            "rows before they roll back. Set RADAR_TEST_HOSTED=1 only in the workflow made for it."
        )
    try:
        with psycopg.connect(DB_URL, connect_timeout=3) as conn:
            ready = conn.execute("select to_regclass('public.reviewers') is not null").fetchone()[0]
    except psycopg.OperationalError as exc:
        msg = f"local Supabase Postgres is not running (supabase db start): {exc}"
        if REQUIRE_DB:
            pytest.fail(msg)
        pytest.skip(msg)
    if not ready:
        pytest.fail("migrations are not applied. Run: supabase db reset")


@pytest.fixture
def db(_db_available: None, request: pytest.FixtureRequest) -> Iterator[psycopg.Connection]:
    if not is_local(DB_URL) and request.node.path.name not in HOSTED_FILES:
        pytest.fail(f"{request.node.path.name} is not one of the files that may run there.")
    conn = psycopg.connect(DB_URL)
    try:
        # Open the transaction here. A `with conn.transaction()` block inside a test is then
        # always a savepoint, never a transaction of its own that commits when it ends.
        conn.execute("select 1")
        if RESIDENTS:
            residents(conn)
        yield conn
    finally:
        conn.rollback()
        conn.close()


# --- acting as someone --------------------------------------------------------------------------


@contextmanager
def _as_role(conn: psycopg.Connection, role: str, claims: dict | None) -> Iterator[None]:
    conn.execute(
        "select set_config('request.jwt.claims', %s, true)",
        [json.dumps(claims) if claims else ""],
    )
    conn.execute(f"set local role {role}")
    try:
        yield
    finally:
        # If the transaction is already broken the test is failing anyway. Do not mask the error.
        if conn.info.transaction_status != psycopg.pq.TransactionStatus.INERROR:
            conn.execute("reset role")
            conn.execute("select set_config('request.jwt.claims', '', true)")


def as_user(conn: psycopg.Connection, user_id: uuid.UUID):
    """Act as a signed-in user, the way a request with that user's token does."""
    return _as_role(conn, "authenticated", {"sub": str(user_id), "role": "authenticated"})


def as_anon(conn: psycopg.Connection):
    """Act as a request that carries only the anonymous key."""
    return _as_role(conn, "anon", {"role": "anon"})


def as_service(conn: psycopg.Connection):
    """Act as a job that holds the service role key. It bypasses RLS but not triggers."""
    return _as_role(conn, "service_role", {"role": "service_role"})


# --- expecting a refusal ------------------------------------------------------------------------


def refused(conn: psycopg.Connection, sql: str, params: list | None = None) -> bool:
    """True when the statement was refused.

    Postgres refuses in two ways. A missing privilege, a failed policy check or one of our
    guard triggers raises an error. An UPDATE or DELETE on rows a policy hides just touches
    zero rows. Both count. The statement runs in a savepoint so the test can go on.
    """
    try:
        with conn.transaction():
            cur = conn.execute(sql, params)
            return cur.rowcount == 0
    except (psycopg.errors.InsufficientPrivilege, psycopg.errors.CheckViolation):
        return True


# --- seed data, inserted as the database owner --------------------------------------------------


def make_user(conn: psycopg.Connection, label: str = "user", verified: bool = False) -> uuid.UUID:
    """An account. `verified` is what the sign-in service records once the person has opened
    the link it emailed to that address."""
    uid = uuid.uuid4()
    conn.execute(
        """insert into auth.users (id, email, email_confirmed_at)
           values (%s, %s, case when %s then now() end)""",
        [uid, f"{label}-{uid.hex[:8]}@example.org", verified],
    )
    return uid


def make_reviewer(
    conn: psycopg.Connection, status: str = "approved", role: str = "reviewer"
) -> uuid.UUID:
    """Create a reviewer row by hand, the way the owner creates the first administrator."""
    uid = make_user(conn, f"{role}-{status}")
    conn.execute(
        """insert into public.reviewers (user_id, display_name, agreed_terms_at, status, role)
           values (%s, %s, now(), %s, %s)""",
        [uid, f"{role} {status}", status, role],
    )
    return uid


def make_site(conn: psycopg.Connection, label: str = "Test tract") -> int:
    """A candidate site with one source, one document and one signal."""
    source_id = conn.execute(
        """insert into public.sources (slug, state, name, url, method, cadence, robots_status)
           values (%s, 'TX', 'Test source', 'https://example.gov/notices', 'manual', 'daily',
                   'not_checked')
           returning id""",
        [f"tx_test_{uuid.uuid4().hex[:8]}"],
    ).fetchone()[0]
    doc_id = conn.execute(
        """insert into public.documents (source_id, url, retrieved_at, sha256, text, county_fips)
           values (%s, 'https://example.gov/notices/1', now(), %s, 'notice text', '48221')
           returning id""",
        [source_id, uuid.uuid4().hex + uuid.uuid4().hex],
    ).fetchone()[0]
    site_id = conn.execute(
        """insert into public.sites (state, county_fips, label, geom)
           values ('TX', '48221', %s,
                   extensions.st_setsrid(extensions.st_makepoint(-97.79, 32.44), 4326))
           returning id""",
        [label],
    ).fetchone()[0]
    conn.execute(
        """insert into public.signals (document_id, signal_type, event_date, summary, site_id,
                                       confidence)
           values (%s, 'abatement_notice', current_date, 'Notice of abatement hearing', %s, 0.9)""",
        [doc_id, site_id],
    )
    return site_id


def confirm(conn: psycopg.Connection, reviewer: uuid.UUID, site_id: int) -> int:
    """The reviewer confirms the site through the API path."""
    with as_user(conn, reviewer):
        return conn.execute(
            """insert into public.reviews (site_id, reviewer_id, decision, source_checked)
               values (%s, %s, 'confirm', true) returning id""",
            [site_id, reviewer],
        ).fetchone()[0]


# --- records that were there before the test ----------------------------------------------------


def residents(conn: psycopg.Connection) -> None:
    """Fill the database the way a running radar fills it, inside the test's transaction.

    The hosted database holds records. A policy test that passes only on empty tables says
    nothing about it. With these in place a test must tell its own rows from someone else's.
    """
    admin = make_reviewer(conn, role="admin")
    make_reviewer(conn)
    make_reviewer(conn, status="pending")
    make_site(conn, "Resident candidate")
    in_review = make_site(conn, "Resident in review")
    conn.execute("update public.sites set status = 'in_review' where id = %s", [in_review])
    published = make_site(conn, "Resident published")
    confirm(conn, admin, published)
    with as_user(conn, admin):
        conn.execute(
            """insert into public.alerts (site_id, headline, body, published_at)
               values (%s, 'Resident alert', 'Body', now())""",
            [published],
        )
    subscriber = make_user(conn, "resident-subscriber", verified=True)
    with as_user(conn, subscriber):
        conn.execute(
            "insert into public.subscribers (user_id, states) values (%s, '{TX}')", [subscriber]
        )
