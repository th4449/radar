"""Alert emails by state. See BUILD_PLAN.md section 7 and config/email.yaml.

    uv run python -m pipeline.alert_email --kind weekly
    uv run python -m pipeline.alert_email --kind each --state TX

The command only does dry runs. Sending real email is the owner's decision (section 11), and
no sender for a real provider is written yet. A dry run works out exactly what would be sent
and reports it in counts, with one sample of each message. It prints no address and no
unsubscribe token, and it records nothing as sent.

Who gets what:

  Only confirmed alerts, read through the same public view the site reads.
  Only subscribers who confirmed, and whose address still matches their account.
  Only alerts published after the person confirmed. Nobody is sent the back catalog.
  An alert reaches a person once. alert_sends is the record.
  A county list narrows a state only if it names a county in that state.

Two kinds of email, the person's choice: `each` is one email per alert, `weekly` is one digest
per selected state. A week with no alert in a state sends nothing for it.

The job connects as the database owner through DATABASE_URL, like the processing job. It reads
each address from the sign-in service's own table, which the service role cannot read.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import sys
import uuid
from collections.abc import Sequence
from typing import Literal, Protocol

import psycopg

from pipeline.config import EmailFile, load_all_counties, load_email

Kind = Literal["each", "weekly"]

STATE_NAMES = {"TX": "Texas", "MI": "Michigan"}
PRODUCT = "Data Center Early Warning Radar"
NOT_SET = "[not set]"

# One disclaimer per email. The alert itself is written by an administrator.
STANDING = (
    "A signal is a public record, not a finding. Confirmed means a reviewer checked each "
    "record against its source. It does not mean a data center is planned."
)

_MONTHS = (
    "January", "February", "March", "April", "May", "June", "July", "August", "September",
    "October", "November", "December",
)  # fmt: skip


class NotReady(RuntimeError):
    """Real sending was asked for and something it needs is missing."""


@dataclasses.dataclass(frozen=True)
class AlertItem:
    alert_id: int
    state: str
    county_fips: str
    headline: str
    body: str
    published_at: dt.datetime
    sources: int


@dataclasses.dataclass(frozen=True)
class Message:
    """One email to one person. `to` and `token` never leave this process in a dry run."""

    user_id: uuid.UUID
    to: str
    token: uuid.UUID
    kind: Kind
    state: str
    alert_ids: tuple[int, ...]
    subject: str
    text: str


class Sender(Protocol):
    def send(self, batch: Sequence[Message]) -> None:
        """Hand one batch to the provider. Raise if any of it was not accepted."""


@dataclasses.dataclass
class Report:
    kind: Kind
    dry_run: bool
    as_of: str
    status: str = "ok"
    alerts: int = 0
    recipients: int = 0
    messages: int = 0
    held_over: int = 0
    batches: int = 0
    by_state: dict[str, dict[str, int]] = dataclasses.field(default_factory=dict)
    address_changed: int = 0
    not_set: list[str] = dataclasses.field(default_factory=list)
    samples: list[dict[str, str]] = dataclasses.field(default_factory=list)
    error: str | None = None

    def detail(self) -> dict:
        """What goes in the run log. Counts only."""
        return {
            "as_of": self.as_of,
            "by_state": self.by_state,
            "batches": self.batches,
            "address_changed": self.address_changed,
            "not_set": self.not_set,
        }


# --- words --------------------------------------------------------------------------------------


def _long_date(when: dt.datetime | dt.date) -> str:
    return f"{_MONTHS[when.month - 1]} {when.day}, {when.year}"


class Places:
    """County names by code, for the lines that say where an alert is."""

    def __init__(self) -> None:
        self._names = {
            c.fips: c.name for state in ("TX", "MI") for c in load_all_counties(state).counties
        }

    def county(self, fips: str) -> str:
        name = self._names.get(fips)
        return f"{name} County" if name else f"County {fips}"

    def where(self, alert: AlertItem) -> str:
        return f"{self.county(alert.county_fips)}, {STATE_NAMES.get(alert.state, alert.state)}"


def _site(settings: EmailFile) -> str:
    return settings.site_url or NOT_SET


def alert_url(settings: EmailFile, alert_id: int) -> str:
    return f"{_site(settings)}/alert/?id={alert_id}"


def _footer(settings: EmailFile, state: str, token: str) -> str:
    state_name = STATE_NAMES.get(state, state)
    return "\n".join(
        [
            "-- ",
            f"You get this email because you signed up for {state_name} alerts from the "
            f"{PRODUCT} and confirmed your address.",
            f"Change what you get: {_site(settings)}/account/",
            f"Unsubscribe: {_site(settings)}/unsubscribe/?token={token}",
            "",
            settings.organization,
            settings.postal_address or f"Postal address {NOT_SET}",
        ]
    )


def _sources_line(count: int) -> str:
    return "1 public record" if count == 1 else f"{count} public records"


def render_each(
    alert: AlertItem, settings: EmailFile, places: Places, token: str
) -> tuple[str, str]:
    """The subject and text of the email for one alert."""
    subject = f"Confirmed alert in {places.where(alert)}: {alert.headline}"
    text = "\n".join(
        [
            alert.headline,
            "",
            f"Confirmed. Published {_long_date(alert.published_at)}.",
            f"{places.where(alert)}.",
            "",
            alert.body.strip(),
            "",
            f"This alert rests on {_sources_line(alert.sources)}. Each one is linked from "
            "the alert page:",
            alert_url(settings, alert.alert_id),
            "",
            STANDING,
            "",
            f"Send a correction: {_site(settings)}/corrections/?alert={alert.alert_id}",
            "",
            _footer(settings, alert.state, token),
        ]
    )
    return subject, text


def render_weekly(
    state: str, alerts: Sequence[AlertItem], settings: EmailFile, places: Places, token: str
) -> tuple[str, str]:
    """The subject and text of one state's digest."""
    state_name = STATE_NAMES.get(state, state)
    count = "1 confirmed alert" if len(alerts) == 1 else f"{len(alerts)} confirmed alerts"
    lines = [f"{state_name}: {count} since your last digest.", ""]
    for alert in alerts:
        lines += [
            alert.headline,
            f"Confirmed. Published {_long_date(alert.published_at)}. "
            f"{places.county(alert.county_fips)}. {_sources_line(alert.sources).capitalize()}.",
            alert_url(settings, alert.alert_id),
            "",
        ]
    lines += [
        STANDING,
        "",
        f"Send a correction: {_site(settings)}/corrections/",
        "",
        _footer(settings, state, token),
    ]
    return f"{state_name} weekly digest: {count}", "\n".join(lines)


# --- who is due what ----------------------------------------------------------------------------

_DUE = """
select s.user_id, u.email::text, s.unsubscribe_token,
       a.alert_id, a.state, a.county_fips, a.headline, a.body, a.published_at,
       jsonb_array_length(a.sources)
from public.subscribers s
join auth.users u
  on u.id = s.user_id and u.email = s.email and u.email_confirmed_at is not null
join public.public_alerts a
  on a.state = any (s.states)
 and a.published_at >= s.confirmed_at
 and a.published_at <= %(as_of)s
 and (s.county_fips is null
      or a.county_fips = any (s.county_fips)
      -- a list that names no county in this state leaves the state whole
      or not exists (select 1 from unnest(s.county_fips) as c (fips)
                     where left(c.fips, 2) = left(a.county_fips, 2)))
where s.confirmed_at is not null
  and s.frequency = %(kind)s
  and (%(state)s::text is null or a.state = %(state)s)
  and not exists (select 1 from public.alert_sends x
                  where x.user_id = s.user_id and x.alert_id = a.alert_id)
order by a.published_at, a.alert_id, s.user_id
"""

_ADDRESS_CHANGED = """
select count(*) from public.subscribers s
join auth.users u on u.id = s.user_id
where s.confirmed_at is not null and (u.email is distinct from s.email)
"""


def due_messages(
    conn: psycopg.Connection,
    *,
    kind: Kind,
    as_of: dt.datetime,
    settings: EmailFile,
    state: str | None = None,
    places: Places | None = None,
) -> list[Message]:
    """Every message that is due, oldest alert first."""
    places = places or Places()
    rows = conn.execute(_DUE, {"kind": kind, "as_of": as_of, "state": state}).fetchall()
    grouped: dict[tuple, list[AlertItem]] = {}
    for user_id, email, token, *alert in rows:
        item = AlertItem(*alert)
        key = (user_id, email, token, item.state) + ((item.alert_id,) if kind == "each" else ())
        grouped.setdefault(key, []).append(item)

    messages = []
    for (user_id, email, token, alert_state, *_), alerts in grouped.items():
        if kind == "each":
            subject, text = render_each(alerts[0], settings, places, str(token))
        else:
            subject, text = render_weekly(alert_state, alerts, settings, places, str(token))
        messages.append(
            Message(
                user_id=user_id,
                to=email,
                token=token,
                kind=kind,
                state=alert_state,
                alert_ids=tuple(a.alert_id for a in alerts),
                subject=subject,
                text=text,
            )
        )
    return messages


def _sample(message: Message) -> dict[str, str]:
    """A message as a person may read it in a log: no address, no working unsubscribe link."""
    return {
        "kind": message.kind,
        "state": message.state,
        "to": "(one subscriber)",
        "subject": message.subject,
        "text": message.text.replace(str(message.token), "TOKEN"),
    }


# --- the run ------------------------------------------------------------------------------------


def run(
    conn: psycopg.Connection,
    *,
    kind: Kind,
    sender: Sender | None = None,
    as_of: dt.datetime | None = None,
    state: str | None = None,
    settings: EmailFile | None = None,
) -> Report:
    """One run of the email job. With no sender it is a dry run."""
    settings = settings or load_email()
    as_of = as_of or dt.datetime.now(dt.UTC)
    dry_run = sender is None
    report = Report(kind=kind, dry_run=dry_run, as_of=as_of.isoformat())
    report.not_set = settings.missing()
    if not dry_run and report.not_set:
        raise NotReady(f"config/email.yaml does not set: {', '.join(report.not_set)}")

    run_id = conn.execute(
        "insert into public.email_runs (kind, dry_run) values (%s, %s) returning id",
        [kind, dry_run],
    ).fetchone()[0]
    done: list[Message] = []
    try:
        with conn.transaction():
            messages = due_messages(conn, kind=kind, as_of=as_of, settings=settings, state=state)
            report.address_changed = conn.execute(_ADDRESS_CHANGED).fetchone()[0]
        today, later = messages[: settings.daily_limit], messages[settings.daily_limit :]
        report.held_over = len(later)
        report.by_state = {
            name: {
                "messages": sum(1 for m in today if m.state == name),
                "alerts": len({a for m in today if m.state == name for a in m.alert_ids}),
            }
            for name in sorted({m.state for m in today})
        }
        report.samples = [
            _sample(next(m for m in today if m.state == name)) for name in report.by_state
        ]
        size = settings.batch_size
        batches = [today[i : i + size] for i in range(0, len(today), size)]
        report.batches = len(batches)
        if dry_run:
            done = today
        else:
            for batch in batches:
                sender.send(batch)
                # Recorded only after the provider took the batch. If recording fails the
                # batch can go twice, which is the safer of the two mistakes.
                with conn.transaction():
                    conn.cursor().executemany(
                        """insert into public.alert_sends (user_id, alert_id, kind)
                           values (%s, %s, %s) on conflict do nothing""",
                        [(m.user_id, a, kind) for m in batch for a in m.alert_ids],
                    )
                done += batch
    except Exception as exc:
        report.status = "failed"
        report.error = f"{type(exc).__name__}: {exc}"
    report.messages = len(done)
    report.recipients = len({m.user_id for m in done})
    report.alerts = len({a for m in done for a in m.alert_ids})
    conn.execute(
        """update public.email_runs
           set finished_at = now(), status = %s, alerts = %s, recipients = %s, messages = %s,
               held_over = %s, detail = %s, error = %s
           where id = %s""",
        [
            report.status,
            report.alerts,
            report.recipients,
            report.messages,
            report.held_over,
            json.dumps(report.detail()),
            report.error,
            run_id,
        ],
    )
    return report


def describe(report: Report) -> str:
    """The report as plain text for a terminal or a job log."""
    lines = [
        f"{'Dry run' if report.dry_run else 'Run'} of the {report.kind} emails as of "
        f"{report.as_of}: {report.status}.",
        f"{report.messages} messages to {report.recipients} subscribers about "
        f"{report.alerts} alerts, in {report.batches} batches.",
    ]
    for name in sorted(report.by_state):
        counts = report.by_state[name]
        lines.append(
            f"  {STATE_NAMES.get(name, name)}: {counts['messages']} messages, "
            f"{counts['alerts']} alerts"
        )
    if report.held_over:
        lines.append(f"{report.held_over} more messages wait for the next run: the daily limit.")
    if report.address_changed:
        lines.append(
            f"{report.address_changed} confirmed subscribers changed their account address and "
            "get nothing until they confirm again."
        )
    if report.not_set:
        lines.append(f"Not set in config/email.yaml: {', '.join(report.not_set)}.")
    if report.error:
        lines.append(f"Error: {report.error}")
    if report.dry_run:
        lines.append("Nothing was sent and nothing was recorded as sent.")
    for sample in report.samples:
        lines += [
            "",
            f"--- sample, {STATE_NAMES.get(sample['state'], sample['state'])} ---",
            f"To: {sample['to']}",
            f"Subject: {sample['subject']}",
            "",
            sample["text"],
        ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Work out the alert emails that are due. Dry run only: nothing is sent."
    )
    parser.add_argument("--kind", choices=["each", "weekly"], required=True)
    parser.add_argument("--state", choices=sorted(STATE_NAMES), help="only this state")
    args = parser.parse_args(argv)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("not started: set DATABASE_URL", file=sys.stderr)
        return 2
    with psycopg.connect(database_url, autocommit=True) as conn:
        report = run(conn, kind=args.kind, state=args.state)
    print(describe(report))
    return 0 if report.status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
