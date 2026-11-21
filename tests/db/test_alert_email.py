"""The alert email job against the database: who is due what, and what a dry run leaves behind."""

from __future__ import annotations

import datetime as dt
import uuid

import psycopg
import pytest

from pipeline import alert_email
from pipeline.config import load_email

from .conftest import as_user, confirm, make_reviewer, make_user

pytestmark = pytest.mark.db

SETTINGS = load_email().model_copy(
    update={
        "site_url": "https://radar.example.org",
        "postal_address": "1 Example Street, Austin, TX 78701",
    }
)
HOOD, HILL, WASHTENAW = "48221", "48217", "26161"
# The settings file with nothing filled in by the owner.
BLANK = load_email().model_copy(update={"site_url": None, "postal_address": None})


def scalar(conn: psycopg.Connection, sql: str, params: list | None = None):
    return conn.execute(sql, params).fetchone()[0]


class World:
    """An administrator, and helpers to publish alerts and sign people up."""

    def __init__(self, conn: psycopg.Connection) -> None:
        self.conn = conn
        self.admin = make_reviewer(conn, role="admin")
        self.source = conn.execute(
            """insert into public.sources (slug, state, name, url, method, cadence)
               values (%s, 'TX', 'Test source', 'https://example.gov/n', 'manual', 'daily')
               returning id""",
            [f"tx_test_{uuid.uuid4().hex[:8]}"],
        ).fetchone()[0]

    def alert(self, headline: str, county: str = HOOD, published: bool = True) -> int:
        conn, state = self.conn, "TX" if county.startswith("48") else "MI"
        doc = conn.execute(
            """insert into public.documents (source_id, url, retrieved_at, sha256)
               values (%s, 'https://example.gov/n/1', now(), %s) returning id""",
            [self.source, uuid.uuid4().hex + uuid.uuid4().hex],
        ).fetchone()[0]
        site = conn.execute(
            "insert into public.sites (state, county_fips, label) values (%s, %s, %s) returning id",
            [state, county, headline],
        ).fetchone()[0]
        conn.execute(
            """insert into public.signals (document_id, signal_type, event_date, summary, site_id)
               values (%s, 'air_permit', current_date, 'Permit application', %s)""",
            [doc, site],
        )
        confirm(conn, self.admin, site)
        with as_user(conn, self.admin):
            return conn.execute(
                """insert into public.alerts (site_id, headline, body, published_at)
                   values (%s, %s, 'Two records name this tract.', %s) returning id""",
                [site, headline, dt.datetime.now(dt.UTC) if published else None],
            ).fetchone()[0]

    def subscriber(
        self,
        states: str = "{TX}",
        *,
        frequency: str = "weekly",
        counties: str | None = None,
        confirmed: bool = True,
    ) -> uuid.UUID:
        conn = self.conn
        user = make_user(conn, "sub", verified=True)
        with as_user(conn, user):
            conn.execute(
                """insert into public.subscribers (user_id, states, county_fips, frequency)
                   values (%s, %s, %s, %s)""",
                [user, states, counties, frequency],
            )
            if confirmed:
                conn.execute("select public.confirm_subscription()")
        if confirmed:
            # The clock does not move inside one test. Put the confirmation in the past.
            conn.execute(
                """update public.subscribers set confirmed_at = now() - interval '1 day'
                   where user_id = %s""",
                [user],
            )
        return user

    def now(self) -> dt.datetime:
        """The database's clock, which stamps the alerts. This machine's can differ a little."""
        return self.conn.execute("select clock_timestamp()").fetchone()[0]

    def due(self, kind: str, **more) -> list[alert_email.Message]:
        return alert_email.due_messages(
            self.conn, kind=kind, as_of=self.now(), settings=SETTINGS, **more
        )


class Outbox:
    def __init__(self, fail_after: int | None = None) -> None:
        self.batches: list[list[alert_email.Message]] = []
        self.fail_after = fail_after

    def send(self, batch) -> None:
        if self.fail_after is not None and len(self.batches) >= self.fail_after:
            raise RuntimeError("the provider refused the batch")
        self.batches.append(list(batch))


# --- who is due what ----------------------------------------------------------------------------


def test_only_confirmed_subscribers_are_sent_anything(db):
    world = World(db)
    world.alert("Signals near Granbury")
    yes = world.subscriber()
    world.subscriber(confirmed=False)
    assert [m.user_id for m in world.due("weekly")] == [yes]


def test_only_published_alerts_are_sent(db):
    world = World(db)
    world.subscriber()
    world.alert("A draft", published=False)
    assert world.due("weekly") == []
    kept = world.alert("Signals near Granbury")
    assert [m.alert_ids for m in world.due("weekly")] == [(kept,)]


def test_an_alert_that_was_taken_down_is_not_sent(db):
    world = World(db)
    world.subscriber()
    alert = world.alert("Signals near Granbury")
    with as_user(db, world.admin):
        db.execute("update public.alerts set published_at = null where id = %s", [alert])
    assert world.due("weekly") == []


def test_nobody_is_sent_alerts_from_before_they_confirmed(db):
    world = World(db)
    world.alert("Signals near Granbury")
    world.subscriber()
    db.execute("update public.subscribers set confirmed_at = now() + interval '1 minute'")
    assert world.due("weekly") == []


def test_each_state_gets_its_own_digest(db):
    world = World(db)
    tx1, tx2 = world.alert("Signals near Granbury"), world.alert("Signals near Hillsboro", HILL)
    mi = world.alert("Signals near Saline", WASHTENAW)
    both = world.subscriber("{TX,MI}")
    world.subscriber("{MI}")
    messages = world.due("weekly")
    mine = {m.state: m.alert_ids for m in messages if m.user_id == both}
    assert mine == {"TX": (tx1, tx2), "MI": (mi,)}
    assert len(messages) == 3
    assert {m.state for m in world.due("weekly", state="MI")} == {"MI"}


def test_each_alert_is_its_own_email_for_those_who_chose_that(db):
    world = World(db)
    a, b = world.alert("Signals near Granbury"), world.alert("Signals near Hillsboro", HILL)
    user = world.subscriber(frequency="each")
    world.subscriber(frequency="weekly")
    messages = world.due("each")
    assert [(m.user_id, m.alert_ids) for m in messages] == [(user, (a,)), (user, (b,))]
    assert len(world.due("weekly")) == 1


def test_a_county_list_narrows_only_the_state_it_names(db):
    world = World(db)
    hood = world.alert("Signals near Granbury", HOOD)
    world.alert("Signals near Hillsboro", HILL)
    saline = world.alert("Signals near Saline", WASHTENAW)
    world.subscriber("{TX,MI}", counties="{" + HOOD + "}")
    got = {m.state: m.alert_ids for m in world.due("weekly")}
    assert got == {"TX": (hood,), "MI": (saline,)}


def test_a_person_who_changed_their_account_address_gets_nothing_until_they_confirm(db):
    world = World(db)
    world.alert("Signals near Granbury")
    user = world.subscriber()
    db.execute("update auth.users set email = 'moved@example.org' where id = %s", [user])
    assert world.due("weekly") == []
    report = alert_email.run(db, kind="weekly", settings=SETTINGS)
    assert report.address_changed == 1


# --- a dry run ----------------------------------------------------------------------------------


def test_a_dry_run_reports_counts_and_records_nothing_as_sent(db):
    world = World(db)
    world.alert("Signals near Granbury")
    world.alert("Signals near Saline", WASHTENAW)
    world.subscriber("{TX,MI}")
    world.subscriber("{TX}")
    report = alert_email.run(db, kind="weekly", settings=SETTINGS)
    assert (report.dry_run, report.status) == (True, "ok")
    assert (report.messages, report.recipients, report.alerts) == (3, 2, 2)
    assert report.by_state == {
        "MI": {"messages": 1, "alerts": 1},
        "TX": {"messages": 2, "alerts": 1},
    }
    assert scalar(db, "select count(*) from public.alert_sends") == 0
    # So the same alerts are still due.
    assert alert_email.run(db, kind="weekly", settings=SETTINGS).messages == 3


def test_a_dry_run_never_shows_an_address_or_a_working_unsubscribe_link(db):
    world = World(db)
    world.alert("Signals near Granbury")
    user = world.subscriber()
    email, token = db.execute(
        "select email, unsubscribe_token::text from public.subscribers where user_id = %s", [user]
    ).fetchone()
    report = alert_email.run(db, kind="weekly", settings=SETTINGS)
    shown = alert_email.describe(report) + str(report.detail()) + str(report.samples)
    logged = db.execute("select row_to_json(r)::text from public.email_runs r").fetchall()
    for text in (shown, str(logged)):
        assert email not in text
        assert token not in text
        assert "example.org/unsubscribe" not in text or "token=TOKEN" in text
    assert "Signals near Granbury" in shown


def test_a_dry_run_says_what_the_owner_has_not_set(db):
    World(db)
    report = alert_email.run(db, kind="each", settings=BLANK)
    assert report.not_set == ["postal_address", "site_url"]
    assert "postal_address" in alert_email.describe(report)


def test_the_run_is_logged_with_counts(db):
    world = World(db)
    world.alert("Signals near Granbury")
    world.subscriber()
    alert_email.run(db, kind="weekly", settings=SETTINGS)
    row = db.execute(
        """select kind, dry_run, status, alerts, recipients, messages, held_over,
                  finished_at is not null from public.email_runs"""
    ).fetchall()
    assert row == [("weekly", True, "ok", 1, 1, 1, 0, True)]


# --- sending, with a stand-in for the provider --------------------------------------------------


def test_real_sending_is_refused_until_the_address_and_site_are_set(db):
    World(db)
    with pytest.raises(alert_email.NotReady, match="postal_address"):
        alert_email.run(db, kind="weekly", sender=Outbox(), settings=BLANK)
    assert scalar(db, "select count(*) from public.email_runs") == 0


def test_real_sending_is_still_refused_with_the_settings_file_as_it_stands(db):
    """The postal address is set. The site's address is not, so nothing can be sent."""
    World(db)
    with pytest.raises(alert_email.NotReady, match="site_url"):
        alert_email.run(db, kind="weekly", sender=Outbox(), settings=load_email())


def test_a_sent_alert_is_not_sent_again(db):
    world = World(db)
    alert = world.alert("Signals near Granbury")
    user = world.subscriber()
    outbox = Outbox()
    first = alert_email.run(db, kind="weekly", sender=outbox, settings=SETTINGS)
    assert (first.dry_run, first.messages) == (False, 1)
    assert db.execute("select user_id, alert_id, kind from public.alert_sends").fetchall() == [
        (user, alert, "weekly")
    ]
    again = alert_email.run(db, kind="weekly", sender=outbox, settings=SETTINGS)
    assert again.messages == 0
    assert len(outbox.batches) == 1
    # Not as the other kind of email either, if the person switches.
    db.execute("update public.subscribers set frequency = 'each'")
    assert world.due("each") == []


def test_the_daily_limit_holds_the_rest_for_the_next_run(db):
    world = World(db)
    world.alert("Signals near Granbury")
    for _ in range(5):
        world.subscriber()
    tight = SETTINGS.model_copy(update={"daily_limit": 3, "batch_size": 2})
    outbox = Outbox()
    first = alert_email.run(db, kind="weekly", sender=outbox, settings=tight)
    assert (first.messages, first.held_over, first.batches) == (3, 2, 2)
    assert [len(b) for b in outbox.batches] == [2, 1]
    second = alert_email.run(db, kind="weekly", sender=outbox, settings=tight)
    assert (second.messages, second.held_over) == (2, 0)
    assert scalar(db, "select count(*) from public.alert_sends") == 5


def test_a_refused_batch_stops_the_run_and_keeps_what_was_sent(db):
    world = World(db)
    world.alert("Signals near Granbury")
    for _ in range(4):
        world.subscriber()
    small = SETTINGS.model_copy(update={"batch_size": 2})
    report = alert_email.run(db, kind="weekly", sender=Outbox(fail_after=1), settings=small)
    assert report.status == "failed"
    assert "refused" in report.error
    assert report.messages == 2
    assert scalar(db, "select count(*) from public.alert_sends") == 2
    assert scalar(db, "select status from public.email_runs") == "failed"
    # The two that did not go are still due.
    assert len(world.due("weekly")) == 2


def test_unsubscribing_ends_the_emails(db):
    world = World(db)
    world.alert("Signals near Granbury")
    user = world.subscriber()
    token = scalar(
        db, "select unsubscribe_token from public.subscribers where user_id = %s", [user]
    )
    db.execute("select public.unsubscribe(%s)", [token])
    assert world.due("weekly") == []
