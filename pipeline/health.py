"""Which sources need a person. BUILD_PLAN.md milestone M10: monitoring for failed collectors.

    uv run python -m pipeline.health

needs DATABASE_URL. It reads the run log and writes nothing. The exit code is 0 when no source
needs a person, 1 when one does and 2 when it could not start.

Every collector run and every processing run is logged, success or failure. This reads the log
and gives each watched source one state:

- `ok`           read cleanly, and recently enough for its cadence.
- `failing`      the newest run failed or was partial. A person reads the error.
- `blocked`      the site refused. **Nobody runs it again.** A person decides what happens next.
- `stuck`        a run started hours ago and never finished.
- `stale`        no clean run within its cadence, with a margin.
- `never_run`    no run is logged.
- `due_by_hand`  a page a person saves is older than its cadence. See collectors/by_hand.py.

A source is watched when a job may read it or a person saves it by hand. A source held for a
permission, and a lookup service, is not: nothing is supposed to run.

The command sends nothing. A scheduled workflow that runs it fails when a source needs a
person, and GitHub then emails the account that set the schedule. See docs/runbook.md.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import psycopg

from pipeline.config import Source, load_sources

# How long a source may go without a clean run before it is stale. A margin over its cadence,
# so that one late run is not an alarm.
ALLOWANCE = {
    "daily": dt.timedelta(days=2),
    "weekly": dt.timedelta(days=9),
    "monthly": dt.timedelta(days=35),
    "yearly": dt.timedelta(days=400),
}
STUCK_AFTER = dt.timedelta(hours=3)  # the longest workflow has a 90 minute limit
PROCESSING_ALLOWANCE = dt.timedelta(days=2)
NOT_OK = ("failed", "partial")


@dataclass(frozen=True)
class Run:
    """One collector run, as the log has it."""

    source_id: str
    started_at: dt.datetime
    finished_at: dt.datetime | None
    status: str
    documents_seen: int
    documents_new: int
    errors: int
    error: str | None


@dataclass(frozen=True)
class Step:
    """One processing run, as the log has it."""

    started_at: dt.datetime
    finished_at: dt.datetime | None
    status: str
    errors: int
    error: str | None


@dataclass(frozen=True)
class Health:
    source_id: str
    state: str
    last_run: dt.datetime | None
    last_ok: dt.datetime | None
    note: str

    @property
    def needs_a_person(self) -> bool:
        return self.state != "ok"


def watched(source: Source) -> bool:
    """A job may read it, or a person saves it. A lookup is asked one record at a time."""
    return source.layer != "lookup" and (source.may_fetch_automatically or source.hand_saved)


def _days(span: dt.timedelta) -> str:
    days = span.days
    return "1 day" if days == 1 else f"{days} days"


def _judge(
    name: str,
    runs: Sequence[Run | Step],
    now: dt.datetime,
    allowance: dt.timedelta | None,
    *,
    by_hand: bool = False,
) -> Health:
    """One state from the runs of one source, newest first."""
    ordered = sorted(runs, key=lambda r: r.started_at, reverse=True)
    last_run = ordered[0].started_at if ordered else None
    clean = [r for r in ordered if r.status == "ok" and r.finished_at is not None]
    last_ok = clean[0].finished_at if clean else None

    def health(state: str, note: str) -> Health:
        return Health(name, state, last_run, last_ok, note)

    if by_hand:
        overdue = last_ok is None or (allowance is not None and now - last_ok > allowance)
        if overdue:
            since = "No copy is stored." if last_ok is None else (
                f"The newest copy is {_days(now - last_ok)} old."
            )  # fmt: skip
            return health(
                "due_by_hand",
                f"{since} A person saves the page in a browser and stores it with "
                f"python -m collectors.by_hand {name} <file>.",
            )
        return health("ok", f"A person stored a copy {_days(now - last_ok)} ago.")
    if not ordered:
        return health("never_run", "No run is logged.")

    # A run still going is judged by the runs before it, unless it has gone on too long.
    newest = ordered[0]
    if newest.status == "running":
        if now - newest.started_at > STUCK_AFTER:
            return health(
                "stuck", f"A run started {_days(now - newest.started_at)} ago and never finished."
            )
        ordered = ordered[1:]
        if not ordered:
            return health("ok", "The first run is going now.")
        newest = ordered[0]

    if newest.status == "blocked":
        return health(
            "blocked",
            f"The site refused: {newest.error or 'no reason logged'}. Do not run it again. "
            "A person reads the source note and decides.",
        )
    if newest.status in NOT_OK:
        in_a_row = 0
        for r in ordered:
            if r.status not in NOT_OK:
                break
            in_a_row += 1
        count = "1 run" if in_a_row == 1 else f"{in_a_row} runs in a row"
        return health(
            "failing", f"{count} did not finish clean. The newest: {newest.error or 'no error'}."
        )
    if allowance is not None and last_ok is not None and now - last_ok > allowance:
        return health("stale", f"No clean run for {_days(now - last_ok)}.")
    return health("ok", "Read cleanly." if last_ok else "No clean run yet.")


def check(sources: Iterable[Source], runs: Iterable[Run], now: dt.datetime) -> list[Health]:
    """The state of every watched source, the ones that need a person first."""
    by_source: dict[str, list[Run]] = {}
    for r in runs:
        by_source.setdefault(r.source_id, []).append(r)
    found = [
        _judge(s.id, by_source.get(s.id, []), now, ALLOWANCE.get(s.cadence), by_hand=s.hand_saved)
        for s in sources
        if watched(s)
    ]
    return sorted(found, key=lambda h: (not h.needs_a_person, h.source_id))


def check_processing(steps: Iterable[Step], now: dt.datetime) -> Health:
    """The state of the step that turns stored documents into signals and sites."""
    return _judge("processing", list(steps), now, PROCESSING_ALLOWANCE)


def report(found: Sequence[Health], processing: Health, now: dt.datetime) -> str:
    """What a person reads. It names sources and never a person or an address."""
    need = [h for h in found if h.needs_a_person]
    lines = [
        f"Radar health, {now:%B} {now.day}, {now.year} {now:%H:%M} UTC",
        f"{len(need)} of {len(found)} sources need a person."
        + ("" if processing.state == "ok" else " So does processing."),
        "",
    ]
    for h in (*found, processing):
        last = "never" if h.last_ok is None else f"{h.last_ok:%Y-%m-%d}"
        mark = "NEEDS A PERSON" if h.needs_a_person else "ok"
        lines.append(f"{mark:15} {h.source_id}: {h.state}. {h.note} Last clean run: {last}.")
    return "\n".join(lines)


# --- reading the log ----------------------------------------------------------------------------

RUNS_KEPT = 20  # the newest runs of each source are enough to judge it


def load_runs(conn: psycopg.Connection) -> list[Run]:
    rows = conn.execute(
        """select slug, started_at, finished_at, status, documents_seen, documents_new, errors,
                  error
           from (select s.slug, r.*, row_number() over (
                          partition by r.source_id order by r.started_at desc, r.id desc) as n
                 from public.collector_runs r join public.sources s on s.id = r.source_id) x
           where n <= %s""",
        [RUNS_KEPT],
    ).fetchall()
    return [Run(*row) for row in rows]


def load_steps(conn: psycopg.Connection) -> list[Step]:
    rows = conn.execute(
        """select started_at, finished_at, status, errors, error
           from public.processing_runs order by started_at desc, id desc limit %s""",
        [RUNS_KEPT],
    ).fetchall()
    return [Step(*row) for row in rows]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Say which sources need a person.")
    parser.add_argument("--json", action="store_true", help="print the states as JSON")
    args = parser.parse_args(argv)
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("not started: set DATABASE_URL", file=sys.stderr)
        return 2
    now = dt.datetime.now(dt.UTC)
    with psycopg.connect(database_url) as conn:
        conn.read_only = True
        found = check(load_sources().sources, load_runs(conn), now)
        processing = check_processing(load_steps(conn), now)
    if args.json:
        rows = [dataclasses.asdict(h) | {"needs_a_person": h.needs_a_person} for h in found]
        rows.append(dataclasses.asdict(processing) | {"needs_a_person": processing.needs_a_person})
        print(json.dumps(rows, indent=2, default=str))
    else:
        print(report(found, processing, now))
    return 1 if processing.needs_a_person or any(h.needs_a_person for h in found) else 0


if __name__ == "__main__":
    raise SystemExit(main())
