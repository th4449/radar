"""Tests for the rules in BUILD_PLAN.md section 7, enforced in the database.

These were written before the policies. Each test names the rule it protects.
"""

from __future__ import annotations

import psycopg
import pytest

from .conftest import (
    as_anon,
    as_service,
    as_user,
    confirm,
    make_reviewer,
    make_site,
    make_user,
    refused,
)

pytestmark = pytest.mark.db

TABLES = [
    "sources",
    "documents",
    "signals",
    "entities",
    "sites",
    "reviews",
    "alerts",
    "reviewers",
    "subscribers",
    "audit_log",
    "app_settings",
    "collector_runs",
    "processing_runs",
    "model_usage",
    "corrections",
    "alert_sends",
    "email_runs",
    "study_payers",
    "entity_study_payers",
]


def scalar(conn: psycopg.Connection, sql: str, params: list | None = None):
    return conn.execute(sql, params).fetchone()[0]


def publish_as_admin(conn, admin, site_id) -> int:
    with as_user(conn, admin):
        return scalar(
            conn,
            """insert into public.alerts (site_id, headline, body, published_at)
               values (%s, 'Signals in Hood County', 'Body', now()) returning id""",
            [site_id],
        )


# --- structure ----------------------------------------------------------------------------------


def test_every_public_table_has_rls_enabled(db):
    rows = db.execute(
        """select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
           where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity"""
    ).fetchall()
    assert rows == [], f"tables without row level security: {rows}"


def test_the_expected_tables_exist(db):
    found = {
        r[0]
        for r in db.execute(
            "select tablename from pg_tables where schemaname = 'public'"
        ).fetchall()
    }
    assert set(TABLES) <= found


def test_defaults_are_one_confirmation_and_admin_gate_on(db):
    row = db.execute(
        "select confirmations_required, admin_gate_enabled from public.app_settings"
    ).fetchall()
    assert row == [(1, True)]


# --- anonymous key ------------------------------------------------------------------------------


@pytest.mark.parametrize("table", TABLES)
def test_anon_cannot_read_any_table(db, table):
    make_site(db)
    with as_anon(db), pytest.raises(psycopg.errors.InsufficientPrivilege), db.transaction():
        db.execute(f"select * from public.{table} limit 1")


@pytest.mark.parametrize("table", TABLES)
def test_anon_cannot_write_any_table(db, table):
    with as_anon(db):
        assert refused(db, f"delete from public.{table}")
        assert refused(db, f"insert into public.{table} default values")


def test_anon_reads_only_published_alerts_with_their_sources(db):
    admin = make_reviewer(db, role="admin")
    reviewer = make_reviewer(db)
    published_site = make_site(db, "Published tract")
    pending_site = make_site(db, "Unpublished tract")
    confirm(db, reviewer, published_site)
    confirm(db, reviewer, pending_site)
    publish_as_admin(db, admin, published_site)
    with as_user(db, admin):
        db.execute(
            "insert into public.alerts (site_id, headline, body) values (%s, 'Draft', 'Draft')",
            [pending_site],
        )

    with as_anon(db):
        rows = db.execute(
            "select label, status, state, county_fips, sources from public.public_alerts "
            "where site_id = any(%s)",
            [[published_site, pending_site]],
        ).fetchall()

    assert len(rows) == 1
    label, status, state, county, sources = rows[0]
    assert (label, status, state, county) == ("Published tract", "confirmed", "TX", "48221")
    assert len(sources) == 1
    assert sources[0]["url"] == "https://example.gov/notices/1"
    assert sources[0]["signal_type"] == "abatement_notice"
    assert set(sources[0]) == {
        "url", "source", "retrieved_at", "sha256", "signal_type", "event_date", "reference"
    }  # fmt: skip
    assert sources[0]["reference"] is None  # this signal was not made by the pipeline


def test_public_view_exposes_no_reviewer_or_subscriber_columns(db):
    cols = {
        r[0]
        for r in db.execute(
            """select column_name from information_schema.columns
               where table_schema = 'public' and table_name = 'public_alerts'"""
        ).fetchall()
    }
    assert cols == {
        "alert_id", "site_id", "headline", "body", "published_at", "confirmed_by_count",
        "status", "state", "county_fips", "label", "geometry", "sources", "study_payers",
    }  # fmt: skip


# --- subscribers --------------------------------------------------------------------------------


def test_anyone_signed_in_can_subscribe_and_defaults_to_weekly_digest(db):
    user = make_user(db, "sub")
    email = scalar(db, "select email from auth.users where id = %s", [user])
    with as_user(db, user):
        db.execute(
            "insert into public.subscribers (user_id, states) values (%s, '{TX,MI}')", [user]
        )
        row = db.execute(
            "select email, frequency, confirmed_at, states from public.subscribers"
        ).fetchall()
    assert row == [(email, "weekly", None, ["TX", "MI"])]


def test_subscriber_cannot_pick_the_email_or_confirm_themselves(db):
    """Double opt in. The address comes from the account and only a trusted job confirms it."""
    user = make_user(db, "sub")
    with as_user(db, user):
        assert refused(
            db,
            """insert into public.subscribers (user_id, states, email)
               values (%s, '{TX}', 'someone.else@example.org')""",
            [user],
        )
        assert refused(
            db,
            """insert into public.subscribers (user_id, states, confirmed_at)
               values (%s, '{TX}', now())""",
            [user],
        )
        db.execute("insert into public.subscribers (user_id, states) values (%s, '{TX}')", [user])
        assert refused(db, "update public.subscribers set confirmed_at = now()")
        assert refused(db, "update public.subscribers set email = 'x@example.org'")
    assert (
        scalar(db, "select confirmed_at from public.subscribers where user_id = %s", [user]) is None
    )


def test_subscriber_cannot_subscribe_someone_else(db):
    user, other = make_user(db, "sub"), make_user(db, "other")
    with as_user(db, user):
        assert refused(
            db, "insert into public.subscribers (user_id, states) values (%s, '{TX}')", [other]
        )


def test_subscriber_cannot_see_or_change_another_subscriber(db):
    a, b = make_user(db, "a"), make_user(db, "b")
    for u in (a, b):
        with as_user(db, u):
            db.execute("insert into public.subscribers (user_id, states) values (%s, '{MI}')", [u])
    with as_user(db, a):
        assert scalar(db, "select count(*) from public.subscribers") == 1
        assert refused(
            db, "update public.subscribers set frequency = 'each' where user_id = %s", [b]
        )
        assert refused(db, "delete from public.subscribers where user_id = %s", [b])
    assert (
        scalar(db, "select frequency from public.subscribers where user_id = %s", [b]) == "weekly"
    )


def test_subscriber_can_narrow_change_frequency_and_unsubscribe(db):
    user = make_user(db, "sub")
    with as_user(db, user):
        db.execute("insert into public.subscribers (user_id, states) values (%s, '{TX}')", [user])
        db.execute("update public.subscribers set county_fips = '{48221}', frequency = 'each'")
        assert db.execute("select county_fips, frequency from public.subscribers").fetchall() == [
            (["48221"], "each")
        ]
        db.execute("delete from public.subscribers")
        assert scalar(db, "select count(*) from public.subscribers") == 0


def test_only_texas_and_michigan_can_be_selected(db):
    user = make_user(db, "sub")
    with as_user(db, user):
        assert refused(
            db, "insert into public.subscribers (user_id, states) values (%s, '{OH}')", [user]
        )
        assert refused(
            db, "insert into public.subscribers (user_id, states) values (%s, '{}')", [user]
        )


def test_signing_up_for_alerts_grants_no_review_rights(db):
    user = make_user(db, "sub")
    site = make_site(db)
    with as_user(db, user):
        db.execute("insert into public.subscribers (user_id, states) values (%s, '{TX}')", [user])
        for table in ("sites", "documents", "signals", "sources", "entities", "reviews", "alerts"):
            assert scalar(db, f"select count(*) from public.{table}") == 0
        assert refused(
            db,
            """insert into public.reviews (site_id, reviewer_id, decision, source_checked)
               values (%s, %s, 'confirm', true)""",
            [site, user],
        )


def test_admin_cannot_read_subscriber_emails(db):
    admin = make_reviewer(db, role="admin")
    user = make_user(db, "sub")
    with as_user(db, user):
        db.execute("insert into public.subscribers (user_id, states) values (%s, '{TX}')", [user])
    with as_user(db, admin):
        assert scalar(db, "select count(*) from public.subscribers") == 0


# --- applying to review -------------------------------------------------------------------------


def test_anyone_may_apply_and_starts_pending_with_no_rights(db):
    user = make_user(db, "applicant")
    site = make_site(db)
    with as_user(db, user):
        db.execute(
            """insert into public.reviewers (user_id, display_name, agreed_terms_at)
               values (%s, 'Pat Applicant', now())""",
            [user],
        )
        assert db.execute("select status, role, approved_by from public.reviewers").fetchall() == [
            ("pending", "reviewer", None)
        ]
        assert scalar(db, "select count(*) from public.sites") == 0
        assert refused(
            db,
            """insert into public.reviews (site_id, reviewer_id, decision, source_checked)
               values (%s, %s, 'confirm', true)""",
            [site, user],
        )


def test_applicant_must_agree_to_the_terms(db):
    user = make_user(db, "applicant")
    with as_user(db, user):
        assert refused(
            db,
            "insert into public.reviewers (user_id, display_name) values (%s, 'No Terms')",
            [user],
        )


@pytest.mark.parametrize(
    "columns,values",
    [
        ("status", "'approved'"),
        ("role", "'admin'"),
        ("status, role", "'approved', 'admin'"),
        ("approved_at", "now()"),
    ],
)
def test_applicant_cannot_apply_as_approved_or_admin(db, columns, values):
    user = make_user(db, "applicant")
    with as_user(db, user):
        assert refused(
            db,
            f"""insert into public.reviewers (user_id, display_name, agreed_terms_at, {columns})
                values (%s, 'Sneaky', now(), {values})""",
            [user],
        )
    assert scalar(db, "select count(*) from public.reviewers where user_id = %s", [user]) == 0


def test_user_cannot_apply_on_behalf_of_someone_else(db):
    user, other = make_user(db, "a"), make_user(db, "b")
    with as_user(db, user):
        assert refused(
            db,
            """insert into public.reviewers (user_id, display_name, agreed_terms_at)
               values (%s, 'Other', now())""",
            [other],
        )


# --- approval is the organization's alone -------------------------------------------------------


def test_pending_reviewer_cannot_confirm_an_alert(db):
    pending = make_reviewer(db, status="pending")
    site = make_site(db)
    with as_user(db, pending):
        assert refused(
            db,
            """insert into public.reviews (site_id, reviewer_id, decision, source_checked)
               values (%s, %s, 'confirm', true)""",
            [site, pending],
        )
        assert refused(
            db,
            """insert into public.alerts (site_id, headline, body, published_at)
               values (%s, 'h', 'b', now())""",
            [site],
        )
    assert scalar(db, "select count(*) from public.reviews where site_id = %s", [site]) == 0
    assert scalar(db, "select count(*) from public.alerts where site_id = %s", [site]) == 0


def test_user_cannot_approve_themselves(db):
    pending = make_reviewer(db, status="pending")
    with as_user(db, pending):
        assert refused(
            db, "update public.reviewers set status = 'approved' where user_id = %s", [pending]
        )
        assert refused(
            db, "update public.reviewers set role = 'admin' where user_id = %s", [pending]
        )
        assert refused(
            db, "update public.reviewers set approved_at = now() where user_id = %s", [pending]
        )
    assert db.execute(
        "select status, role, approved_by, approved_at from public.reviewers where user_id = %s",
        [pending],
    ).fetchall() == [("pending", "reviewer", None, None)]


def test_approved_reviewer_cannot_make_themselves_admin_or_approve_others(db):
    reviewer = make_reviewer(db)
    pending = make_reviewer(db, status="pending")
    with as_user(db, reviewer):
        assert refused(
            db, "update public.reviewers set role = 'admin' where user_id = %s", [reviewer]
        )
        assert refused(
            db, "update public.reviewers set status = 'approved' where user_id = %s", [pending]
        )
        # A reviewer does not even see other applicants.
        assert scalar(db, "select count(*) from public.reviewers") == 1
    assert scalar(db, "select role from public.reviewers where user_id = %s", [reviewer]) == (
        "reviewer"
    )
    assert scalar(db, "select status from public.reviewers where user_id = %s", [pending]) == (
        "pending"
    )


def test_admin_approves_and_the_approval_is_recorded(db):
    admin = make_reviewer(db, role="admin")
    pending = make_reviewer(db, status="pending")
    with as_user(db, admin):
        db.execute("update public.reviewers set status = 'approved' where user_id = %s", [pending])
    status, approved_by, approved_at = db.execute(
        "select status, approved_by, approved_at from public.reviewers where user_id = %s",
        [pending],
    ).fetchone()
    assert (status, approved_by) == ("approved", admin)
    assert approved_at is not None


def test_admin_cannot_forge_who_approved(db):
    admin, other_admin = make_reviewer(db, role="admin"), make_reviewer(db, role="admin")
    pending = make_reviewer(db, status="pending")
    with as_user(db, admin):
        assert refused(
            db,
            "update public.reviewers set status = 'approved', approved_by = %s where user_id = %s",
            [other_admin, pending],
        )


def test_admin_cannot_change_their_own_status(db):
    """Nobody acts on their own reviewer row, administrators included."""
    admin = make_reviewer(db, role="admin")
    db.execute("update public.reviewers set status = 'suspended' where user_id = %s", [admin])
    with as_user(db, admin):
        assert refused(
            db, "update public.reviewers set status = 'approved' where user_id = %s", [admin]
        )
    assert scalar(db, "select status from public.reviewers where user_id = %s", [admin]) == (
        "suspended"
    )


def test_admin_cannot_grant_the_admin_role_through_the_app(db):
    """There is no self-service path to admin. The owner grants it by hand in SQL."""
    admin = make_reviewer(db, role="admin")
    reviewer = make_reviewer(db)
    with as_user(db, admin):
        assert refused(
            db, "update public.reviewers set role = 'admin' where user_id = %s", [reviewer]
        )
    assert scalar(db, "select role from public.reviewers where user_id = %s", [reviewer]) == (
        "reviewer"
    )


def test_service_role_cannot_approve_suspend_or_promote(db):
    """Approval is never automated. A job holding the service key is refused."""
    pending = make_reviewer(db, status="pending")
    reviewer = make_reviewer(db)
    user = make_user(db, "new")
    with as_service(db):
        assert refused(
            db, "update public.reviewers set status = 'approved' where user_id = %s", [pending]
        )
        assert refused(
            db, "update public.reviewers set status = 'suspended' where user_id = %s", [reviewer]
        )
        assert refused(
            db, "update public.reviewers set role = 'admin' where user_id = %s", [reviewer]
        )
        assert refused(
            db,
            """insert into public.reviewers (user_id, display_name, agreed_terms_at, status)
               values (%s, 'Auto', now(), 'approved')""",
            [user],
        )
        assert refused(db, "delete from public.reviewers where user_id = %s", [reviewer])
    assert scalar(db, "select status from public.reviewers where user_id = %s", [pending]) == (
        "pending"
    )


def test_suspended_admin_loses_admin_rights(db):
    admin = make_reviewer(db, status="suspended", role="admin")
    pending = make_reviewer(db, status="pending")
    with as_user(db, admin):
        assert refused(
            db, "update public.reviewers set status = 'approved' where user_id = %s", [pending]
        )


# --- reviewing ----------------------------------------------------------------------------------


def test_approved_reviewer_confirms_after_ticking_source_checked(db):
    reviewer = make_reviewer(db)
    site = make_site(db)
    with as_user(db, reviewer):
        assert scalar(db, "select count(*) from public.sites where id = %s", [site]) == 1
        assert (
            scalar(
                db,
                """select count(*) from public.documents d
                   where exists (select 1 from public.signals s
                                 where s.document_id = d.id and s.site_id = %s)""",
                [site],
            )
            == 1
        )
        for decision in ("confirm", "reject"):
            assert refused(
                db,
                """insert into public.reviews (site_id, reviewer_id, decision, source_checked)
                   values (%s, %s, %s, false)""",
                [site, reviewer, decision],
            )
        db.execute(
            """insert into public.reviews (site_id, reviewer_id, decision, source_checked, note)
               values (%s, %s, 'confirm', true, 'Matches the county notice.')""",
            [site, reviewer],
        )
    assert scalar(db, "select status from public.sites where id = %s", [site]) == "in_review"


def test_reviewer_cannot_review_in_another_reviewers_name(db):
    reviewer, other = make_reviewer(db), make_reviewer(db)
    site = make_site(db)
    with as_user(db, reviewer):
        assert refused(
            db,
            """insert into public.reviews (site_id, reviewer_id, decision, source_checked)
               values (%s, %s, 'confirm', true)""",
            [site, other],
        )


def test_service_role_cannot_write_a_review(db):
    reviewer = make_reviewer(db)
    site = make_site(db)
    with as_service(db):
        assert refused(
            db,
            """insert into public.reviews (site_id, reviewer_id, decision, source_checked)
               values (%s, %s, 'confirm', true)""",
            [site, reviewer],
        )


def test_suspended_reviewer_cannot_review(db):
    suspended = make_reviewer(db, status="suspended")
    site = make_site(db)
    with as_user(db, suspended):
        assert scalar(db, "select count(*) from public.sites") == 0
        assert refused(
            db,
            """insert into public.reviews (site_id, reviewer_id, decision, source_checked)
               values (%s, %s, 'confirm', true)""",
            [site, suspended],
        )


@pytest.mark.parametrize(
    "statement",
    [
        "update public.documents set text = 'edited'",
        "update public.documents set url = 'https://example.com/other'",
        "delete from public.documents",
        "update public.signals set summary = 'edited'",
        "update public.signals set confidence = 1",
        "delete from public.signals",
        "update public.sites set score = 999",
        "update public.sites set status = 'confirmed'",
        "delete from public.sites",
        "update public.entities set name = 'edited'",
        "update public.sources set url = 'https://example.com'",
        "insert into public.sites (state, county_fips, label) values ('TX', '48221', 'made up')",
    ],
)
@pytest.mark.parametrize("who", ["reviewer", "admin"])
def test_reviewers_cannot_edit_documents_signals_or_scores(db, statement, who):
    actor = make_reviewer(db, role="admin" if who == "admin" else "reviewer")
    make_site(db)
    db.execute(
        "insert into public.entities (name, normalized_name, kind)"
        " values ('Acme LLC', 'ACME LLC', 'company')"
    )
    with as_user(db, actor):
        assert refused(db, statement)


def test_reviewer_cannot_change_or_delete_a_review_after_the_fact(db):
    reviewer = make_reviewer(db)
    site = make_site(db)
    review = confirm(db, reviewer, site)
    with as_user(db, reviewer):
        assert refused(db, "update public.reviews set decision = 'reject' where id = %s", [review])
        assert refused(db, "update public.reviews set reversed_at = now() where id = %s", [review])
        assert refused(db, "delete from public.reviews where id = %s", [review])


def test_admin_can_suspend_a_reviewer_and_reverse_their_decisions(db):
    admin = make_reviewer(db, role="admin")
    reviewer = make_reviewer(db)
    site = make_site(db)
    review = confirm(db, reviewer, site)
    with as_user(db, admin):
        db.execute(
            "update public.reviewers set status = 'suspended' where user_id = %s", [reviewer]
        )
        db.execute(
            """update public.reviews set reversed_at = now(), reversal_note = 'Suspended'
               where id = %s""",
            [review],
        )
        # Reversing is the only change an administrator can make to a review.
        assert refused(db, "update public.reviews set decision = 'reject' where id = %s", [review])
    reversed_by = scalar(db, "select reversed_by from public.reviews where id = %s", [review])
    assert reversed_by == admin


# --- publishing ---------------------------------------------------------------------------------


def test_alert_cannot_be_published_without_a_confirmation(db):
    admin = make_reviewer(db, role="admin")
    site = make_site(db)
    with as_user(db, admin):
        assert refused(
            db,
            """insert into public.alerts (site_id, headline, body, published_at)
               values (%s, 'h', 'b', now())""",
            [site],
        )


def test_unsure_reviews_do_not_count_as_confirmations(db):
    admin = make_reviewer(db, role="admin")
    reviewer = make_reviewer(db)
    site = make_site(db)
    with as_user(db, reviewer):
        db.execute(
            "insert into public.reviews (site_id, reviewer_id, decision) values (%s, %s, 'unsure')",
            [site, reviewer],
        )
    with as_user(db, admin):
        assert refused(
            db,
            """insert into public.alerts (site_id, headline, body, published_at)
               values (%s, 'h', 'b', now())""",
            [site],
        )


def test_while_the_gate_is_on_only_an_admin_publishes(db):
    admin = make_reviewer(db, role="admin")
    reviewer = make_reviewer(db)
    site = make_site(db)
    confirm(db, reviewer, site)

    publish = """insert into public.alerts (site_id, headline, body, published_at)
                 values (%s, 'h', 'b', now())"""
    with as_user(db, reviewer):
        assert refused(db, publish, [site])
    with as_service(db):
        assert refused(db, publish, [site])
        # A job may draft an alert. It may not publish it.
        db.execute(
            "insert into public.alerts (site_id, headline, body) values (%s, 'h', 'b')", [site]
        )
        assert refused(
            db, "update public.alerts set published_at = now() where site_id = %s", [site]
        )

    with as_user(db, admin):
        db.execute("update public.alerts set published_at = now() where site_id = %s", [site])

    approved_by, approved_at, count = db.execute(
        "select approved_by, approved_at, confirmed_by_count from public.alerts where site_id = %s",
        [site],
    ).fetchone()
    assert (approved_by, count) == (admin, 1)
    assert approved_at is not None
    assert scalar(db, "select status from public.sites where id = %s", [site]) == "confirmed"


def test_only_an_admin_can_lift_the_gate_or_change_confirmations_required(db):
    admin = make_reviewer(db, role="admin")
    reviewer = make_reviewer(db)
    with as_user(db, reviewer):
        assert refused(db, "update public.app_settings set admin_gate_enabled = false")
        assert refused(db, "update public.app_settings set confirmations_required = 1")
    with as_service(db):
        assert refused(db, "update public.app_settings set admin_gate_enabled = false")
    with as_user(db, admin):
        db.execute("update public.app_settings set confirmations_required = 2")
        assert refused(db, "update public.app_settings set confirmations_required = 0")
    assert db.execute(
        "select confirmations_required, admin_gate_enabled, updated_by from public.app_settings"
    ).fetchall() == [(2, True, admin)]


def test_two_confirmations_are_needed_when_the_setting_is_two(db):
    admin = make_reviewer(db, role="admin")
    first, second = make_reviewer(db), make_reviewer(db)
    site = make_site(db)
    with as_user(db, admin):
        db.execute("update public.app_settings set confirmations_required = 2")
    confirm(db, first, site)
    publish = """insert into public.alerts (site_id, headline, body, published_at)
                 values (%s, 'h', 'b', now())"""
    with as_user(db, admin):
        assert refused(db, publish, [site])
    confirm(db, second, site)
    with as_user(db, admin):
        db.execute(publish, [site])
    assert (
        scalar(db, "select confirmed_by_count from public.alerts where site_id = %s", [site]) == 2
    )


def test_a_reviewer_cannot_confirm_the_same_site_twice(db):
    reviewer = make_reviewer(db)
    site = make_site(db)
    confirm(db, reviewer, site)
    with as_user(db, reviewer), pytest.raises(psycopg.errors.UniqueViolation), db.transaction():
        db.execute(
            """insert into public.reviews (site_id, reviewer_id, decision, source_checked)
               values (%s, %s, 'confirm', true)""",
            [site, reviewer],
        )


def test_after_the_gate_is_lifted_a_job_can_publish_a_confirmed_site(db):
    admin = make_reviewer(db, role="admin")
    reviewer = make_reviewer(db)
    confirmed_site, unconfirmed_site = make_site(db, "A"), make_site(db, "B")
    confirm(db, reviewer, confirmed_site)
    with as_user(db, admin):
        db.execute("update public.app_settings set admin_gate_enabled = false")
    publish = """insert into public.alerts (site_id, headline, body, published_at)
                 values (%s, 'h', 'b', now())"""
    with as_service(db):
        db.execute(publish, [confirmed_site])
        assert refused(db, publish, [unconfirmed_site])
    with as_anon(db):
        shown = db.execute(
            "select site_id from public.public_alerts where site_id = any(%s)",
            [[confirmed_site, unconfirmed_site]],
        ).fetchall()
        assert shown == [(confirmed_site,)]


def test_reversed_or_suspended_confirmations_do_not_count(db):
    admin = make_reviewer(db, role="admin")
    reversed_reviewer, suspended_reviewer = make_reviewer(db), make_reviewer(db)
    site_a, site_b = make_site(db, "A"), make_site(db, "B")
    review = confirm(db, reversed_reviewer, site_a)
    confirm(db, suspended_reviewer, site_b)
    publish = """insert into public.alerts (site_id, headline, body, published_at)
                 values (%s, 'h', 'b', now())"""
    with as_user(db, admin):
        db.execute("update public.reviews set reversed_at = now() where id = %s", [review])
        db.execute(
            "update public.reviewers set status = 'suspended' where user_id = %s",
            [suspended_reviewer],
        )
        assert refused(db, publish, [site_a])
        assert refused(db, publish, [site_b])


def test_a_standing_rejection_blocks_publication(db):
    admin = make_reviewer(db, role="admin")
    yes, no = make_reviewer(db), make_reviewer(db)
    site = make_site(db)
    confirm(db, yes, site)
    with as_user(db, no):
        db.execute(
            """insert into public.reviews (site_id, reviewer_id, decision, source_checked)
               values (%s, %s, 'reject', true)""",
            [site, no],
        )
    with as_user(db, admin):
        assert refused(
            db,
            """insert into public.alerts (site_id, headline, body, published_at)
               values (%s, 'h', 'b', now())""",
            [site],
        )


def test_approval_fields_cannot_be_forged_or_backdated(db):
    admin, other_admin = make_reviewer(db, role="admin"), make_reviewer(db, role="admin")
    reviewer = make_reviewer(db)
    site = make_site(db)
    other_site = make_site(db, "Other")
    confirm(db, reviewer, site)
    confirm(db, reviewer, other_site)
    forged = """insert into public.alerts
                  (site_id, headline, body, published_at, approved_by, approved_at,
                   confirmed_by_count)
                values (%s, 'h', 'b', '2020-01-01', %s, '2020-01-01', 99)"""
    check = """select approved_by, confirmed_by_count, published_at < now() - interval '1 day'
               from public.alerts where site_id = %s"""
    with as_user(db, admin):
        # Through the app an administrator cannot even name these columns.
        assert refused(db, forged, [site, other_admin])
        db.execute(
            """insert into public.alerts (site_id, headline, body, published_at)
               values (%s, 'h', 'b', '2020-01-01')""",
            [site],
        )
        db.execute("update public.app_settings set admin_gate_enabled = false")
    assert db.execute(check, [site]).fetchone() == (admin, 1, False)
    # A job holding the service key can name them, and the database overwrites what it sent.
    with as_service(db):
        db.execute(forged, [other_site, other_admin])
    assert db.execute(check, [other_site]).fetchone() == (None, 1, False)


def test_reversing_the_last_confirmation_takes_a_published_alert_down(db):
    admin = make_reviewer(db, role="admin")
    reviewer = make_reviewer(db)
    site = make_site(db)
    review = confirm(db, reviewer, site)
    publish_as_admin(db, admin, site)
    with as_user(db, admin):
        db.execute("update public.reviews set reversed_at = now() where id = %s", [review])
    with as_anon(db):
        assert (
            scalar(db, "select count(*) from public.public_alerts where site_id = %s", [site]) == 0
        )
    assert scalar(db, "select status from public.sites where id = %s", [site]) == "in_review"


def test_unpublished_alert_leaves_the_public_view(db):
    admin = make_reviewer(db, role="admin")
    reviewer = make_reviewer(db)
    site = make_site(db)
    confirm(db, reviewer, site)
    alert = publish_as_admin(db, admin, site)
    with as_user(db, admin):
        db.execute("update public.alerts set published_at = null where id = %s", [alert])
    with as_anon(db):
        assert (
            scalar(db, "select count(*) from public.public_alerts where site_id = %s", [site]) == 0
        )


# --- audit log ----------------------------------------------------------------------------------


def test_every_reviewer_action_is_logged(db):
    admin = make_reviewer(db, role="admin")
    applicant = make_user(db, "applicant")
    site = make_site(db)
    with as_user(db, applicant):
        db.execute(
            """insert into public.reviewers (user_id, display_name, agreed_terms_at)
               values (%s, 'Pat', now())""",
            [applicant],
        )
    with as_user(db, admin):
        db.execute(
            "update public.reviewers set status = 'approved' where user_id = %s", [applicant]
        )
    review = confirm(db, applicant, site)
    alert = publish_as_admin(db, admin, site)
    with as_user(db, admin):
        db.execute("update public.reviews set reversed_at = now() where id = %s", [review])
        db.execute(
            "update public.reviewers set status = 'suspended' where user_id = %s", [applicant]
        )
        db.execute("update public.app_settings set confirmations_required = 2")

    log = db.execute(
        "select actor, action, target from public.audit_log where actor in (%s, %s) order by id",
        [admin, applicant],
    ).fetchall()
    assert log == [
        (applicant, "reviewer.applied", str(applicant)),
        (admin, "reviewer.approved", str(applicant)),
        (applicant, "review.confirm", str(site)),
        (admin, "alert.published", str(alert)),
        (admin, "review.reversed", str(review)),
        # Reversing the only confirmation takes the alert down.
        (admin, "alert.unpublished", str(alert)),
        (admin, "reviewer.suspended", str(applicant)),
        (admin, "settings.changed", "app_settings"),
    ]


def test_nobody_can_write_a_fake_audit_entry_through_the_helper(db):
    reviewer = make_reviewer(db)
    for actor in (as_user(db, reviewer), as_service(db), as_anon(db)):
        with actor, pytest.raises(psycopg.errors.InsufficientPrivilege), db.transaction():
            db.execute("select private.log_action('reviewer.approved', 'forged')")


def test_audit_log_is_append_only_and_admin_readable(db):
    admin = make_reviewer(db, role="admin")
    reviewer = make_reviewer(db)
    with as_user(db, reviewer):
        assert scalar(db, "select count(*) from public.audit_log") == 0
        assert refused(db, "insert into public.audit_log (action, target) values ('fake', 'fake')")
    with as_user(db, admin):
        assert scalar(db, "select count(*) from public.audit_log") >= 2
        assert refused(db, "delete from public.audit_log")
        assert refused(db, "update public.audit_log set action = 'edited'")
    with as_service(db):
        assert refused(db, "delete from public.audit_log")
        assert refused(db, "update public.audit_log set action = 'edited'")
    # Even the owner cannot rewrite history without first removing the guard.
    assert refused(db, "delete from public.audit_log")
    assert refused(db, "truncate public.audit_log")
