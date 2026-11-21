"""Fixtures for the policy tests.

The tests run against the local Supabase Postgres (`supabase db start`), because the policies
depend on Supabase's roles and on auth.uid(). Each test runs in one transaction that is rolled
back, so tests never see each other's rows.

A test acts as a user the same way the Supabase API does: it switches to the `authenticated`
role and sets the JWT claims for the request.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
import pytest

DB_URL = os.environ.get(
    "RADAR_TEST_DB_URL", "postgresql://postgres:postgres@127.0.0.1:55322/postgres"
)
REQUIRE_DB = os.environ.get("RADAR_REQUIRE_DB") == "1"

pytestmark = pytest.mark.db


@pytest.fixture(scope="session")
def _db_available() -> None:
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
def db(_db_available: None) -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(DB_URL)
    try:
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
