"""Database rules the reviewer app rests on. Written before the migration.

BUILD_PLAN.md section 7. The app's screens are thin: what a person may do is decided here.
"""

from __future__ import annotations

import uuid

import psycopg
import pytest

from .conftest import as_anon, as_service, as_user, confirm, make_reviewer, make_site, make_user

pytestmark = pytest.mark.db


def status(conn: psycopg.Connection, site_id: int) -> str:
    return conn.execute("select status from public.sites where id = %s", [site_id]).fetchone()[0]


def review(conn, reviewer: uuid.UUID, site_id: int, decision: str, checked: bool = True) -> int:
    with as_user(conn, reviewer):
        return conn.execute(
            """insert into public.reviews (site_id, reviewer_id, decision, source_checked, note)
               values (%s, %s, %s, %s, 'note') returning id""",
            [site_id, reviewer, decision, checked],
        ).fetchone()[0]


def reverse(conn, admin: uuid.UUID, review_id: int) -> None:
    with as_user(conn, admin):
        conn.execute(
            "update public.reviews set reversed_at = now(), reversal_note = 'r' where id = %s",
            [review_id],
        )


def second_site(conn, county: str = "48221") -> int:
    """Another candidate site in the same county, with one signal."""
    first = make_site(conn, "Second tract")
    if county != "48221":
        conn.execute("update public.sites set county_fips = %s where id = %s", [county, first])
    return first


def audit(conn, action: str) -> list[dict]:
    return [
        r[0]
        for r in conn.execute(
            "select detail from public.audit_log where action = %s order by id", [action]
        ).fetchall()
    ]


# --- rejecting a site ---------------------------------------------------------------------------


def test_a_rejection_with_no_confirmation_rejects_the_site(db):
    site_id, reviewer = make_site(db), make_reviewer(db)
    review(db, reviewer, site_id, "reject")
    assert status(db, site_id) == "rejected"


def test_an_unsure_review_only_puts_the_site_in_review(db):
    site_id, reviewer = make_site(db), make_reviewer(db)
    review(db, reviewer, site_id, "unsure", checked=False)
    assert status(db, site_id) == "in_review"


def test_reviewers_who_disagree_leave_the_site_in_review(db):
    site_id = make_site(db)
    confirm(db, make_reviewer(db), site_id)
    review(db, make_reviewer(db), site_id, "reject")
    assert status(db, site_id) == "in_review"

    other = make_site(db, "Other tract")
    review(db, make_reviewer(db), other, "reject")
    confirm(db, make_reviewer(db), other)
    assert status(db, other) == "in_review"


def test_reversing_the_rejection_returns_the_site_to_review(db):
    site_id, reviewer, admin = make_site(db), make_reviewer(db), make_reviewer(db, role="admin")
    review_id = review(db, reviewer, site_id, "reject")
    reverse(db, admin, review_id)
    assert status(db, site_id) == "in_review"


def test_suspending_the_reviewer_who_rejected_returns_the_site_to_review(db):
    site_id, reviewer, admin = make_site(db), make_reviewer(db), make_reviewer(db, role="admin")
    review(db, reviewer, site_id, "reject")
    with as_user(db, admin):
        db.execute(
            "update public.reviewers set status = 'suspended' where user_id = %s", [reviewer]
        )
    assert status(db, site_id) == "in_review"
    # Approving them again makes their rejection stand again.
    with as_user(db, admin):
        db.execute("update public.reviewers set status = 'approved' where user_id = %s", [reviewer])
    assert status(db, site_id) == "rejected"


def test_a_rejection_does_not_take_a_published_site_down_by_itself(db):
    site_id, admin = make_site(db), make_reviewer(db, role="admin")
    confirm(db, make_reviewer(db), site_id)
    with as_user(db, admin):
        db.execute(
            """insert into public.alerts (site_id, headline, body, published_at)
               values (%s, 'Signals in Hood County', 'Body', now())""",
            [site_id],
        )
    review(db, make_reviewer(db), site_id, "reject")
    assert status(db, site_id) == "confirmed"


def test_a_pending_reviewer_cannot_reject_either(db):
    site_id, pending = make_site(db), make_reviewer(db, status="pending")
    with pytest.raises(psycopg.errors.InsufficientPrivilege), db.transaction():
        review(db, pending, site_id, "reject")
    assert status(db, site_id) == "candidate"


# --- applying -----------------------------------------------------------------------------------


def test_an_applicant_can_say_who_they_are_and_cannot_edit_it_later(db):
    user = make_user(db)
    with as_user(db, user):
        db.execute(
            """insert into public.reviewers (user_id, display_name, agreed_terms_at,
                                             application_note)
               values (%s, 'Invented Applicant', now(), 'Retired county clerk, Hood County.')""",
            [user],
        )
        with pytest.raises(psycopg.errors.InsufficientPrivilege), db.transaction():
            db.execute(
                "update public.reviewers set application_note = 'x' where user_id = %s", [user]
            )
    assert db.execute(
        "select status, application_note from public.reviewers where user_id = %s", [user]
    ).fetchone() == ("pending", "Retired county clerk, Hood County.")


def test_an_application_note_has_a_length_limit(db):
    user = make_user(db)
    with (
        as_user(db, user),
        pytest.raises(psycopg.errors.CheckViolation),
        db.transaction(),
    ):
        db.execute(
            """insert into public.reviewers (user_id, display_name, agreed_terms_at,
                                             application_note)
               values (%s, 'Invented Applicant', now(), %s)""",
            [user, "x" * 2001],
        )


# --- the reviewer directory ---------------------------------------------------------------------


def test_an_administrator_sees_who_applied_with_their_email(db):
    admin = make_reviewer(db, role="admin")
    applicant = make_reviewer(db, status="pending")
    with as_user(db, admin):
        rows = db.execute(
            "select user_id, email, status, role from public.reviewer_directory()"
        ).fetchall()
    by_id = {r[0]: r[1:] for r in rows}
    assert by_id[applicant][1:] == ("pending", "reviewer")
    assert by_id[applicant][0].endswith("@example.org")
    assert by_id[admin][1:] == ("approved", "admin")


@pytest.mark.parametrize("who", ["reviewer", "pending", "subscriber", "suspended_admin"])
def test_nobody_else_reads_the_reviewer_directory(db, who):
    make_reviewer(db, status="pending")
    actor = {
        "reviewer": lambda: make_reviewer(db),
        "pending": lambda: make_reviewer(db, status="pending"),
        "subscriber": lambda: make_user(db),
        "suspended_admin": lambda: make_reviewer(db, status="suspended", role="admin"),
    }[who]()
    with (
        as_user(db, actor),
        pytest.raises(psycopg.errors.InsufficientPrivilege),
        db.transaction(),
    ):
        db.execute("select * from public.reviewer_directory()")


def test_the_anonymous_key_and_a_job_cannot_read_the_reviewer_directory(db):
    for role in (as_anon, as_service):
        with (
            role(db),
            pytest.raises(psycopg.errors.InsufficientPrivilege),
            db.transaction(),
        ):
            db.execute("select * from public.reviewer_directory()")


# --- merging two sites that are one place -------------------------------------------------------


def test_an_administrator_folds_one_site_into_another(db):
    admin = make_reviewer(db, role="admin")
    keep, fold = make_site(db, "Kept tract"), second_site(db)
    with as_user(db, admin):
        db.execute("select public.merge_sites(%s, %s, %s)", [fold, keep, "same parcel"])

    assert db.execute("select count(*) from public.sites where id = %s", [fold]).fetchone() == (0,)
    rows = db.execute(
        "select site_id, extracted->>'site_link' from public.signals where site_id = %s", [keep]
    ).fetchall()
    assert len(rows) == 2
    assert ("joined by an administrator" in {r[1] for r in rows}) is True
    (logged,) = audit(db, "site.merged")
    assert logged["from"] == fold and logged["signals_moved"] == 1
    assert logged["from_label"] == "Second tract" and logged["note"] == "same parcel"


@pytest.mark.parametrize("who", ["reviewer", "pending", "subscriber"])
def test_only_an_administrator_merges_sites(db, who):
    keep, fold = make_site(db), second_site(db)
    actor = {
        "reviewer": lambda: make_reviewer(db),
        "pending": lambda: make_reviewer(db, status="pending"),
        "subscriber": lambda: make_user(db),
    }[who]()
    with (
        as_user(db, actor),
        pytest.raises(psycopg.errors.InsufficientPrivilege),
        db.transaction(),
    ):
        db.execute("select public.merge_sites(%s, %s)", [fold, keep])
    assert db.execute("select count(*) from public.sites where id = %s", [fold]).fetchone() == (1,)


def test_a_job_and_the_anonymous_key_cannot_merge_sites(db):
    keep, fold = make_site(db), second_site(db)
    for role in (as_service, as_anon):
        with (
            role(db),
            pytest.raises(psycopg.errors.InsufficientPrivilege),
            db.transaction(),
        ):
            db.execute("select public.merge_sites(%s, %s)", [fold, keep])


def test_sites_in_different_counties_are_not_merged(db):
    admin = make_reviewer(db, role="admin")
    keep, fold = make_site(db), second_site(db, county="48035")
    with (
        as_user(db, admin),
        pytest.raises(psycopg.errors.CheckViolation),
        db.transaction(),
    ):
        db.execute("select public.merge_sites(%s, %s)", [fold, keep])


def test_a_site_that_was_reviewed_is_not_folded_away(db):
    admin, reviewer = make_reviewer(db, role="admin"), make_reviewer(db)
    keep, fold = make_site(db), second_site(db)
    confirm(db, reviewer, fold)
    with (
        as_user(db, admin),
        pytest.raises(psycopg.errors.CheckViolation),
        db.transaction(),
    ):
        db.execute("select public.merge_sites(%s, %s)", [fold, keep])
    # The other way round works: the reviewed site is the one that stays.
    with as_user(db, admin):
        db.execute("select public.merge_sites(%s, %s)", [keep, fold])
    assert db.execute(
        "select count(*) from public.signals where site_id = %s", [fold]
    ).fetchone() == (2,)
    assert db.execute(
        "select count(*) from public.reviews where site_id = %s", [fold]
    ).fetchone() == (1,)


def test_a_site_is_not_merged_into_itself_or_into_nothing(db):
    admin = make_reviewer(db, role="admin")
    site_id = make_site(db)
    for pair in ([site_id, site_id], [site_id, 0], [0, site_id]):
        with (
            as_user(db, admin),
            pytest.raises(psycopg.errors.CheckViolation),
            db.transaction(),
        ):
            db.execute("select public.merge_sites(%s, %s)", pair)
