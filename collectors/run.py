"""Run one collector.

    export RADAR_CONTACT="<the project's public contact address>"
    uv run python -m collectors.run tx_ercot_rpg --dry-run

A dry run fetches the source and reports what it found. It keeps nothing: the run log lives in
memory and the files go to a temporary folder.

A real run needs DATABASE_URL and RADAR_ARCHIVE_DIR. It writes the run log and the documents
to the database and the original files to the archive folder.

A source runs only if config/sources.yaml clears it for automatic fetching. The exit code is 0
for a clean run, 1 for a run that was partial, failed or blocked, and 2 for a run that could
not start.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import tempfile
from pathlib import Path

import httpx
import psycopg

from collectors.base import Collector, Fetcher, LocalArchive, NotPermitted, RunSummary
from collectors.tx.comptroller_data_centers import ComptrollerDataCenters
from collectors.tx.ercot_large_load import ErcotLargeLoad
from collectors.tx.ercot_rpg import ErcotRpg
from collectors.tx.tceq_air_pending_legacy import TceqAirPendingLegacy
from pipeline.config import Source, load_sources
from pipeline.store import MemorySink, PostgresSink

REGISTRY: dict[str, type[Collector]] = {
    c.source_id: c for c in (ComptrollerDataCenters, ErcotRpg, ErcotLargeLoad, TceqAirPendingLegacy)
}


class CannotStart(Exception):
    """The run was not attempted."""


def run_source(
    source: Source,
    *,
    dry_run: bool,
    runner: str | None = None,
    contact: str | None = None,
    transport: httpx.BaseTransport | None = None,
    **fetcher_kwargs,
) -> RunSummary:
    if source.id not in REGISTRY:
        raise CannotStart(f"no collector is written for {source.id}")
    if not source.may_fetch_automatically:
        raise CannotStart(f"{source.id} is marked manual in config/sources.yaml")
    collector = REGISTRY[source.id]()

    def go(store, sink) -> RunSummary:
        with Fetcher(source, contact=contact, transport=transport, **fetcher_kwargs) as fetcher:
            return collector.run(
                source=source, fetcher=fetcher, store=store, sink=sink, runner=runner
            )

    if dry_run:
        with tempfile.TemporaryDirectory(prefix="radar-dry-run-") as tmp:
            return go(LocalArchive(Path(tmp)), MemorySink())

    database_url = os.environ.get("DATABASE_URL")
    archive_dir = os.environ.get("RADAR_ARCHIVE_DIR")
    if not database_url or not archive_dir:
        raise CannotStart("a real run needs DATABASE_URL and RADAR_ARCHIVE_DIR. Or pass --dry-run.")
    with psycopg.connect(database_url, autocommit=True) as conn:
        return go(LocalArchive(Path(archive_dir)), PostgresSink(conn))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one collector.")
    parser.add_argument("source_id", help="the id in config/sources.yaml")
    parser.add_argument("--dry-run", action="store_true", help="fetch and report, keep nothing")
    parser.add_argument("--runner", default=os.environ.get("RADAR_RUNNER", "manual"))
    args = parser.parse_args(argv)

    try:
        source = load_sources().by_id(args.source_id)
    except KeyError:
        print(f"no source with id {args.source_id} in config/sources.yaml", file=sys.stderr)
        return 2
    try:
        summary = run_source(source, dry_run=args.dry_run, runner=args.runner)
    except (CannotStart, NotPermitted) as exc:
        print(f"not started: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(dataclasses.asdict(summary), indent=2))
    return 0 if summary.status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
