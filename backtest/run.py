"""Run the Texas backtest over stored history and write the report. BUILD_PLAN.md milestone M9.

    uv run python -m backtest.run

needs DATABASE_URL and RADAR_ARCHIVE_DIR, set to the history database and its archive. See
CLAUDE.md for where history is kept. It reads only: no table is written and no site is asked
for anything.

The Comptroller's list is the newest copy the history holds. A person saves that page by hand
since November 23, 2026, when the site refused the collector. A history with no copy falls
back on the one saved with the tests on November 19, 2026, the real page of that day.

`--listing` writes every signal to a CSV, with the company each names. **That file is not for
the repository.** A signal that fits no known project is unreviewed, and the public site
shows nothing unreviewed. The command refuses a path inside the repository.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import sys
from pathlib import Path

import psycopg

from backtest.harness import Result, run, sweep
from backtest.history import History, harness_projects, history_rules, listed_since, load
from backtest.projects import load_known_projects
from backtest.report import write
from collectors.base import LocalArchive
from pipeline.config import load_all_counties, load_control_counties, load_scoring
from pipeline.signals import LISTING_SOURCE

REPOSITORY = Path(__file__).resolve().parent.parent
REPORT = REPOSITORY / "backtest" / "report_tx.md"
COMPTROLLER_LIST = (
    REPOSITORY / "tests" / "fixtures" / "tx_comptroller_data_centers" / "data-center-lists.html"
)
HISTORY_STARTS = dt.date(2023, 1, 1)
THRESHOLDS = (1.0, 2.0, 3.0, 4.0, 5.0, 10.0, 20.0, 40.0)


def stored_listing(conn: psycopg.Connection, store: LocalArchive) -> bytes | None:
    """The newest copy of the Comptroller's list the database holds, or None."""
    row = conn.execute(
        """select d.storage_path
           from public.documents d join public.sources s on s.id = d.source_id
           where s.slug = %s
           order by d.retrieved_at desc, d.id desc
           limit 1""",
        [LISTING_SOURCE],
    ).fetchone()
    return store.get(row[0]) if row else None


def judge(history: History, starts: dt.date = HISTORY_STARTS) -> Result:
    """Judge the known projects against the history's signals, at the scoring file's numbers."""
    control = {c.fips for c in load_control_counties("TX").counties}
    # A signal with no county sits on no site, in the backtest as on the radar.
    placed = [s for s in history.signals if s.county_fips]
    projects = harness_projects(load_known_projects(), history)
    return run(projects, placed, load_scoring(), control_fips=control, history_starts=starts)


def write_listing(path: Path, history: History, result: Result) -> None:
    tied = {s.signal_id: o.project.key for o in result.outcomes for s in o.signals}
    counties = {c.fips: c.name for c in load_all_counties("TX").counties}
    with path.open("w", newline="", encoding="utf-8") as out:
        rows = csv.writer(out)
        rows.writerow(
            ("signal", "seen", "dated", "county", "kind", "source", "strongest_reason", "terms",
             "confidence", "party", "record", "address", "known_project", "names_found",
             "fits_two", "seen_basis")
        )  # fmt: skip
        for r in history.records:
            s = r.signal
            rows.writerow(
                (s.signal_id, s.available_on, s.event_date, counties.get(s.county_fips, ""),
                 s.signal_type, s.source_id, r.rule, "; ".join(r.terms), s.confidence,
                 r.party or "", r.reference, r.url, tied.get(s.signal_id, ""),
                 "; ".join(r.named_by), "; ".join(result.ambiguous.get(s.signal_id, ())),
                 r.seen_basis)
            )  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Texas backtest and write its report.")
    parser.add_argument("--out", type=Path, default=REPORT, help="where the report goes")
    parser.add_argument("--listing", type=Path, help="write every signal to this CSV, outside "
                        "the repository")  # fmt: skip
    args = parser.parse_args(argv)

    database_url = os.environ.get("DATABASE_URL")
    archive_dir = os.environ.get("RADAR_ARCHIVE_DIR")
    if not database_url or not archive_dir:
        print("not started: set DATABASE_URL and RADAR_ARCHIVE_DIR", file=sys.stderr)
        return 2
    if args.listing and REPOSITORY in args.listing.resolve().parents:
        print("not started: the listing names unreviewed records. Keep it outside the "
              "repository.", file=sys.stderr)  # fmt: skip
        return 2

    known = load_known_projects()
    store = LocalArchive(Path(archive_dir))
    with psycopg.connect(database_url) as conn:
        conn.read_only = True
        listing = stored_listing(conn, store) or COMPTROLLER_LIST.read_bytes()
        history = load(conn, store, history_rules(listing), known, listed_since(listing))
    result = judge(history)
    control = [c.name for c in load_control_counties("TX").counties]
    report = write(result, history, known, sweep(result, THRESHOLDS), control_names=control)
    args.out.write_text(report + "\n", encoding="utf-8")
    if args.listing:
        write_listing(args.listing, history, result)
    s = result.summary
    print(f"{len(history.records)} signals, {s.judged} projects judged, {s.hits} hits, "
          f"{s.false_alarms} false alarms. Report: {args.out}")  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
