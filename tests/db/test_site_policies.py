"""Who may change a site. Written before the migration.

A site is confirmed or rejected through review. A job that holds the service key scores sites
and moves them into the reviewers' queue. It cannot confirm or reject one.
"""

from __future__ import annotations

import psycopg
import pytest

from .conftest import as_service, as_user, confirm, make_reviewer, make_site, refused

pytestmark = pytest.mark.db


def status(conn: psycopg.Connection, site_id: int) -> str:
    return conn.execute("select status from public.sites where id = %s", [site_id]).fetchone()[0]


def test_a_job_scores_a_site_and_moves_it_into_the_queue(db):
    site_id = make_site(db)
    with as_service(db):
        db.execute(
            """update public.sites
               set score = 54.5, score_detail = '{"score": 54.5}'::jsonb, scored_at = now(),
                   status = 'in_review'
               where id = %s""",
            [site_id],
        )
    row = db.execute(
        "select score, score_detail->>'score', scored_at is not null, status"
        " from public.sites where id = %s",
        [site_id],
    ).fetchone()
    assert row == (54.5, "54.5", True, "in_review")


@pytest.mark.parametrize("to", ["confirmed", "rejected"])
def test_a_job_cannot_confirm_or_reject_a_site(db, to):
    site_id = make_site(db)
    with (
        as_service(db),
        pytest.raises(psycopg.errors.InsufficientPrivilege),
        db.transaction(),
    ):
        db.execute("update public.sites set status = %s where id = %s", [to, site_id])
    assert status(db, site_id) == "candidate"


@pytest.mark.parametrize("to", ["confirmed", "rejected", "in_review"])
def test_a_job_cannot_create_a_site_that_skips_the_queue(db, to):
    with (
        as_service(db),
        pytest.raises(psycopg.errors.InsufficientPrivilege),
        db.transaction(),
    ):
        db.execute(
            "insert into public.sites (state, county_fips, label, status)"
            " values ('TX', '48221', 'made up', %s)",
            [to],
        )


def test_a_job_creates_a_candidate_site(db):
    with as_service(db):
        site_id = db.execute(
            "insert into public.sites (state, county_fips, label) values ('TX', '48221', 'x')"
            " returning id"
        ).fetchone()[0]
    assert status(db, site_id) == "candidate"


def test_a_job_cannot_take_a_confirmed_or_rejected_site_back(db):
    site_id = make_site(db)
    db.execute("update public.sites set status = 'rejected' where id = %s", [site_id])
    with (
        as_service(db),
        pytest.raises(psycopg.errors.InsufficientPrivilege),
        db.transaction(),
    ):
        db.execute("update public.sites set status = 'candidate' where id = %s", [site_id])
    # It can still score it.
    with as_service(db):
        db.execute("update public.sites set score = 3 where id = %s", [site_id])
    assert status(db, site_id) == "rejected"


def test_review_still_moves_a_site_and_publishing_still_confirms_it(db):
    site_id = make_site(db)
    reviewer, admin = make_reviewer(db), make_reviewer(db, role="admin")
    confirm(db, reviewer, site_id)
    assert status(db, site_id) == "in_review"
    with as_user(db, admin):
        db.execute(
            """insert into public.alerts (site_id, headline, body, published_at)
               values (%s, 'Signals in Hood County', 'Body', now())""",
            [site_id],
        )
    assert status(db, site_id) == "confirmed"


@pytest.mark.parametrize("who", ["reviewer", "admin"])
def test_nobody_scores_or_moves_a_site_through_the_app(db, who):
    site_id = make_site(db)
    actor = make_reviewer(db, role="admin" if who == "admin" else "reviewer")
    with as_user(db, actor):
        assert refused(db, "update public.sites set score = 99 where id = %s", [site_id])
        assert refused(db, "update public.sites set status = 'rejected' where id = %s", [site_id])
        assert refused(
            db, "update public.sites set score_detail = '{}'::jsonb where id = %s", [site_id]
        )


def test_a_reviewer_reads_the_breakdown_and_the_public_view_does_not_carry_it(db):
    site_id = make_site(db)
    db.execute(
        """update public.sites set score = 42, score_detail = '{"score": 42}'::jsonb
           where id = %s""",
        [site_id],
    )
    reviewer = make_reviewer(db)
    with as_user(db, reviewer):
        assert db.execute(
            "select score_detail->>'score' from public.sites where id = %s", [site_id]
        ).fetchone() == ("42",)
    columns = {
        r[0]
        for r in db.execute(
            "select column_name from information_schema.columns"
            " where table_schema = 'public' and table_name = 'public_alerts'"
        ).fetchall()
    }
    assert not {"score", "score_detail", "scored_at"} & columns
