"""The test setup itself: nothing a test writes is kept. Written with the change it guards.

Before November 26, 2026 a test whose first statement went through `refused()` ran that
statement as a transaction of its own. Had the statement not been refused, it would have been
committed. On the local database that is one stray row. On the hosted database it could have
been an account or a reviewer.

These run on the local database only. They open a second connection to look from outside.
"""

from __future__ import annotations

import uuid

import psycopg
import pytest

from .conftest import DB_URL, HOSTED_FILES, is_local, refused

pytestmark = pytest.mark.db


def test_a_first_statement_that_is_not_refused_is_still_not_kept(db):
    slug = f"tx_test_{uuid.uuid4().hex[:8]}"
    try:
        # The very first statement of this test, through the helper, and one the owner may make.
        assert not refused(
            db,
            """insert into public.sources (slug, state, name, url, method, cadence, robots_status)
               values (%s, 'TX', 'Test source', 'https://example.gov/x', 'manual', 'daily',
                       'not_checked')""",
            [slug],
        )
        with psycopg.connect(DB_URL) as outside:
            seen = outside.execute(
                "select count(*) from public.sources where slug = %s", [slug]
            ).fetchone()[0]
        assert seen == 0, "the row was committed: another connection can see it"
    finally:
        # If the guard is ever lost, do not leave the row behind.
        with psycopg.connect(DB_URL, autocommit=True) as outside:
            outside.execute("delete from public.sources where slug = %s", [slug])


def test_the_test_transaction_is_open_before_the_test_begins(db):
    assert db.info.transaction_status == psycopg.pq.TransactionStatus.INTRANS


@pytest.mark.parametrize(
    ("url", "local"),
    [
        ("postgresql://postgres:postgres@127.0.0.1:55322/postgres", True),
        ("postgresql://postgres:postgres@localhost:55322/postgres", True),
        ("postgresql://postgres.abc:pw@aws-0-us-east-1.pooler.example.test:5432/postgres", False),
        ("postgresql://postgres:pw@db.abc.example.test:5432/postgres", False),
        ("postgresql:///postgres", False),  # no host named: not known to be this machine
    ],
)
def test_only_an_address_on_this_machine_counts_as_local(url, local):
    assert is_local(url) is local


def test_the_files_that_may_run_elsewhere_are_the_four_policy_files():
    assert {
        "test_policies.py",
        "test_processing_policies.py",
        "test_site_policies.py",
        "test_study_policies.py",
    } == HOSTED_FILES
