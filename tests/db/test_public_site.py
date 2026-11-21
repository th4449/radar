"""Rules the public site and the alert emails rest on. See BUILD_PLAN.md section 7.

Written before the pages. Each test names the rule it protects.

  Double opt in       a subscription counts only after the account's address was proved by an
                      emailed link, and the person confirmed it.
  Unsubscribe         the link in an email works without signing in, for that one person.
  Corrections         anyone may send one. Only an administrator reads them.
  The send ledger     no one but the email job sees it.
"""

from __future__ import annotations

import uuid

import psycopg
import pytest

from .conftest import as_anon, as_user, confirm, make_reviewer, make_site, make_user, refused

pytestmark = pytest.mark.db


def scalar(conn: psycopg.Connection, sql: str, params: list | None = None):
    return conn.execute(sql, params).fetchone()[0]


def subscribe(conn, user, states="{TX}", **more) -> None:
    columns = ["user_id", "states", *more]
    marks = ", ".join(["%s"] * len(columns))
    with as_user(conn, user):
        conn.execute(
            f"insert into public.subscribers ({', '.join(columns)}) values ({marks})",
            [user, states, *more.values()],
        )


def published_alert(conn, label="Published tract") -> int:
    admin = make_reviewer(conn, role="admin")
    site = make_site(conn, label)
    confirm(conn, admin, site)
    with as_user(conn, admin):
        return scalar(
            conn,
            """insert into public.alerts (site_id, headline, body, published_at)
               values (%s, 'Signals in Hood County', 'Body', now()) returning id""",
            [site],
        )


# --- double opt in ------------------------------------------------------------------------------


def test_a_new_subscription_is_not_confirmed(db):
    user = make_user(db, "sub", verified=True)
    subscribe(db, user)
    assert (
        scalar(db, "select confirmed_at from public.subscribers where user_id = %s", [user]) is None
    )


def test_a_person_whose_address_was_proved_by_email_can_confirm(db):
    user = make_user(db, "sub", verified=True)
    subscribe(db, user)
    with as_user(db, user):
        stamp = scalar(db, "select public.confirm_subscription()")
        assert stamp is not None
        assert scalar(db, "select confirmed_at from public.subscribers") == stamp


def test_an_unproved_address_cannot_be_confirmed(db):
    """The second opt in is the emailed link. Without it the address may be someone else's."""
    user = make_user(db, "sub", verified=False)
    subscribe(db, user)
    with as_user(db, user):
        assert refused(db, "select public.confirm_subscription()")
    assert (
        scalar(db, "select confirmed_at from public.subscribers where user_id = %s", [user]) is None
    )


def test_confirming_touches_only_the_callers_own_subscription(db):
    a, b = make_user(db, "a", verified=True), make_user(db, "b", verified=True)
    subscribe(db, a)
    subscribe(db, b)
    with as_user(db, a):
        db.execute("select public.confirm_subscription()")
    assert scalar(db, "select confirmed_at from public.subscribers where user_id = %s", [b]) is None


def test_confirming_without_a_subscription_does_nothing(db):
    user = make_user(db, "nobody", verified=True)
    with as_user(db, user):
        assert scalar(db, "select public.confirm_subscription()") is None
    assert scalar(db, "select count(*) from public.subscribers") == 0


def test_confirming_twice_keeps_the_first_date(db):
    user = make_user(db, "sub", verified=True)
    subscribe(db, user)
    with as_user(db, user):
        first = scalar(db, "select public.confirm_subscription()")
        assert scalar(db, "select public.confirm_subscription()") == first


def test_confirming_takes_the_address_from_the_account_again(db):
    """An account can change its address. The stored copy must not go on receiving alerts."""
    user = make_user(db, "sub", verified=True)
    subscribe(db, user)
    with as_user(db, user):
        db.execute("select public.confirm_subscription()")
    db.execute("update auth.users set email = 'moved@example.org' where id = %s", [user])
    with as_user(db, user):
        db.execute("select public.confirm_subscription()")
        assert scalar(db, "select email from public.subscribers") == "moved@example.org"


def test_the_anonymous_key_cannot_confirm_anything(db):
    with as_anon(db):
        assert refused(db, "select public.confirm_subscription()")


def test_a_subscriber_still_cannot_set_the_confirmation_date_directly(db):
    user = make_user(db, "sub", verified=True)
    subscribe(db, user)
    with as_user(db, user):
        assert refused(db, "update public.subscribers set confirmed_at = now()")


# --- narrowing to counties ----------------------------------------------------------------------


def test_counties_must_be_five_digit_codes_in_a_selected_state(db):
    user = make_user(db, "sub")
    with as_user(db, user):
        for bad in ("{Hood}", "{4822}", "{26161}", "{}"):
            assert refused(
                db,
                """insert into public.subscribers (user_id, states, county_fips)
                   values (%s, '{TX}', %s)""",
                [user, bad],
            ), bad
        db.execute(
            """insert into public.subscribers (user_id, states, county_fips)
               values (%s, '{TX,MI}', '{48221,26161}')""",
            [user],
        )
        # Dropping a state while keeping one of its counties is refused too.
        assert refused(db, "update public.subscribers set states = '{TX}'")


# --- unsubscribe --------------------------------------------------------------------------------


def test_the_link_in_an_email_unsubscribes_without_signing_in(db):
    a, b = make_user(db, "a", verified=True), make_user(db, "b", verified=True)
    subscribe(db, a)
    subscribe(db, b)
    token = scalar(db, "select unsubscribe_token from public.subscribers where user_id = %s", [a])
    with as_anon(db):
        assert scalar(db, "select public.unsubscribe(%s)", [token]) is True
    left = [r[0] for r in db.execute("select user_id from public.subscribers").fetchall()]
    assert left == [b]


def test_a_wrong_token_unsubscribes_no_one(db):
    user = make_user(db, "sub", verified=True)
    subscribe(db, user)
    with as_anon(db):
        assert scalar(db, "select public.unsubscribe(%s)", [uuid.uuid4()]) is False
        assert scalar(db, "select public.unsubscribe(null)") is False
    assert scalar(db, "select count(*) from public.subscribers") == 1


def test_unsubscribing_removes_the_send_history_with_the_address(db):
    user = make_user(db, "sub", verified=True)
    subscribe(db, user)
    alert = published_alert(db)
    db.execute(
        "insert into public.alert_sends (user_id, alert_id, kind) values (%s, %s, 'each')",
        [user, alert],
    )
    token = scalar(
        db, "select unsubscribe_token from public.subscribers where user_id = %s", [user]
    )
    with as_anon(db):
        db.execute("select public.unsubscribe(%s)", [token])
    assert scalar(db, "select count(*) from public.alert_sends") == 0


def test_a_subscriber_cannot_read_anyones_token_but_their_own(db):
    a, b = make_user(db, "a"), make_user(db, "b")
    subscribe(db, a)
    subscribe(db, b)
    with as_user(db, a):
        assert scalar(db, "select count(unsubscribe_token) from public.subscribers") == 1


# --- the send ledger and the run log ------------------------------------------------------------


def test_no_signed_in_user_reads_or_writes_the_send_ledger(db):
    admin = make_reviewer(db, role="admin")
    user = make_user(db, "sub", verified=True)
    subscribe(db, user)
    alert = published_alert(db)
    for who in (admin, user):
        with as_user(db, who):
            with pytest.raises(psycopg.errors.InsufficientPrivilege), db.transaction():
                db.execute("select * from public.alert_sends")
            assert refused(
                db,
                "insert into public.alert_sends (user_id, alert_id, kind) values (%s, %s, 'each')",
                [user, alert],
            )


def test_an_alert_is_recorded_as_sent_to_a_person_once(db):
    user = make_user(db, "sub", verified=True)
    subscribe(db, user)
    alert = published_alert(db)
    sql = "insert into public.alert_sends (user_id, alert_id, kind) values (%s, %s, %s)"
    db.execute(sql, [user, alert, "each"])
    with pytest.raises(psycopg.errors.UniqueViolation), db.transaction():
        db.execute(sql, [user, alert, "weekly"])


def test_only_administrators_read_the_email_run_log_and_it_holds_no_address(db):
    admin = make_reviewer(db, role="admin")
    reviewer = make_reviewer(db)
    db.execute(
        """insert into public.email_runs (kind, dry_run, status) values ('weekly', true, 'ok')"""
    )
    with as_user(db, admin):
        assert scalar(db, "select count(*) from public.email_runs") == 1
    with as_user(db, reviewer):
        assert scalar(db, "select count(*) from public.email_runs") == 0
    columns = {
        r[0]
        for r in db.execute(
            """select column_name from information_schema.columns
               where table_schema = 'public' and table_name = 'email_runs'"""
        ).fetchall()
    }
    assert not {c for c in columns if "email" in c or "address" in c or "token" in c}


# --- corrections --------------------------------------------------------------------------------


def test_anyone_can_send_a_correction_and_cannot_read_it_back(db):
    alert = published_alert(db)
    with as_anon(db):
        db.execute(
            "select public.submit_correction(%s, %s, %s)",
            ["The permit number on this alert is wrong.", alert, "reader@example.org"],
        )
        with pytest.raises(psycopg.errors.InsufficientPrivilege), db.transaction():
            db.execute("select * from public.corrections")
    row = db.execute(
        "select alert_id, message, contact, handled_at from public.corrections"
    ).fetchall()
    assert row == [(alert, "The permit number on this alert is wrong.", "reader@example.org", None)]


def test_a_correction_needs_no_alert_and_no_contact(db):
    with as_anon(db):
        db.execute(
            "select public.submit_correction(%s)", ["The methodology page misstates a rule."]
        )
    assert db.execute("select alert_id, contact from public.corrections").fetchall() == [
        (None, None)
    ]


def test_a_correction_cannot_point_at_an_alert_that_is_not_public(db):
    """Otherwise the form would tell a stranger which unpublished alerts exist."""
    admin = make_reviewer(db, role="admin")
    site = make_site(db, "Draft tract")
    with as_user(db, admin):
        draft = scalar(
            db,
            """insert into public.alerts (site_id, headline, body)
               values (%s, 'Draft', 'Draft') returning id""",
            [site],
        )
    with as_anon(db):
        for alert_id in (draft, 999_999_999):
            assert refused(
                db,
                "select public.submit_correction(%s, %s)",
                ["This alert is wrong, I think.", alert_id],
            )
    assert scalar(db, "select count(*) from public.corrections") == 0


def test_an_empty_or_oversized_correction_is_refused(db):
    with as_anon(db):
        for message in ("", "   ", "short", "x" * 4001):
            assert refused(db, "select public.submit_correction(%s)", [message])
        assert refused(
            db, "select public.submit_correction(%s, null, %s)", ["A real correction.", "c" * 201]
        )


def test_the_form_stops_taking_corrections_when_flooded(db):
    with as_anon(db):
        for n in range(30):
            db.execute("select public.submit_correction(%s)", [f"Correction number {n}, in full."])
        assert refused(db, "select public.submit_correction(%s)", ["One correction too many."])
    assert scalar(db, "select count(*) from public.corrections") == 30


def test_only_an_administrator_reads_corrections(db):
    admin = make_reviewer(db, role="admin")
    reviewer = make_reviewer(db)
    subscriber = make_user(db, "sub")
    with as_anon(db):
        db.execute("select public.submit_correction(%s)", ["The county named here is wrong."])
    with as_user(db, admin):
        assert scalar(db, "select count(*) from public.corrections") == 1
    for who in (reviewer, subscriber):
        with as_user(db, who):
            assert scalar(db, "select count(*) from public.corrections") == 0


def test_an_administrator_marks_a_correction_handled_and_it_is_logged(db):
    admin = make_reviewer(db, role="admin")
    reviewer = make_reviewer(db)
    with as_anon(db):
        db.execute("select public.submit_correction(%s)", ["The county named here is wrong."])
    with as_user(db, reviewer):
        assert refused(db, "update public.corrections set handled_at = now()")
    with as_user(db, admin):
        db.execute("update public.corrections set handled_at = now(), handled_note = 'Fixed.'")
        # The text a reader sent is never edited.
        assert refused(db, "update public.corrections set message = 'changed'")
        assert refused(db, "delete from public.corrections")
    handled_by, note = db.execute(
        "select handled_by, handled_note from public.corrections"
    ).fetchone()
    assert (handled_by, note) == (admin, "Fixed.")
    logged = db.execute(
        "select actor, action from public.audit_log where action = 'correction.handled'"
    ).fetchall()
    assert logged == [(admin, "correction.handled")]


def test_the_audit_log_never_holds_a_readers_contact(db):
    admin = make_reviewer(db, role="admin")
    with as_anon(db):
        db.execute(
            "select public.submit_correction(%s, null, %s)",
            ["The county named here is wrong.", "reader@example.org"],
        )
    with as_user(db, admin):
        db.execute("update public.corrections set handled_at = now(), handled_note = 'Fixed.'")
    assert (
        scalar(db, "select count(*) from public.audit_log where detail::text like '%reader@%'") == 0
    )


# --- what a public alert shows of each record ---------------------------------------------------


def test_a_public_alert_names_each_record_by_its_own_number(db):
    """Two records from one archived file must not look like one record listed twice."""
    alert = published_alert(db)
    db.execute(
        """update public.signals
           set extracted = extracted || '{"reference": "Texas well report tracking number 728122"}'
           where site_id = (select site_id from public.alerts where id = %s)""",
        [alert],
    )
    with as_anon(db):
        sources = scalar(
            db, "select sources from public.public_alerts where alert_id = %s", [alert]
        )
    assert [s["reference"] for s in sources] == ["Texas well report tracking number 728122"]
    # Still nothing written by the pipeline about what the record means, and no party.
    assert set(sources[0]) == {
        "url", "source", "retrieved_at", "sha256", "signal_type", "event_date", "reference"
    }  # fmt: skip
