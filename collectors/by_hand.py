"""Store a page a person saved in a browser. No request is made.

    uv run python -m collectors.by_hand tx_comptroller_data_centers \\
        ~/Downloads/data-center-lists.html

A site can refuse the radar's reader and still publish a page any person may open. When that
happens the source is marked `method: manual` and `hand_saved: true` in config/sources.yaml,
and a person does what the job did:

1. Open the source's page in a browser.
2. Save it as "Webpage, HTML only". Not a web archive and not a PDF.
3. Run this command on the saved file.

The command checks that the file is the page it is said to be, with the same parser the
collector uses. A file it cannot read as that page is refused and nothing is stored: the
refusal page a site shows, a browser's own archive format, the wrong page.

What is stored is what a run stores: the file, the page's address, a time and the file's hash.
The record says a person saved it. The time is the file's own time unless `--saved-at` gives
another, such as `2026-11-24T15:30:00-06:00`. The name of the file is not kept.

It needs DATABASE_URL and RADAR_ARCHIVE_DIR, as a real run does. The exit code is 0 when the
page is stored or was stored before, 1 when the file is refused and 2 when the command could
not start.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import sys
from pathlib import Path

import psycopg

from collectors.base import (
    ArchiveStore,
    FetchResult,
    LayoutChanged,
    LocalArchive,
    RunSummary,
    Sink,
    archive,
)
from collectors.run import REGISTRY
from pipeline.config import Source, load_sources
from pipeline.store import PostgresSink

RUNNER = "by-hand"


class NotStored(Exception):
    """The file was not stored."""


def file_time(path: Path) -> dt.datetime:
    """The file's own time: for a page just saved, the time it was saved."""
    return dt.datetime.fromtimestamp(path.stat().st_mtime, dt.UTC)


def store_saved_page(
    *,
    source: Source,
    path: Path,
    saved_at: dt.datetime,
    store: ArchiveStore,
    sink: Sink,
    now: dt.datetime | None = None,
) -> RunSummary:
    """Check the saved file is the source's page, then store it as a run would."""
    url, body = check(source, path, saved_at, now=now)
    result = FetchResult(
        url=url,
        final_url=url,
        status=200,
        content_type="text/html",
        etag=None,
        last_modified=None,
        body=body,
        retrieved_at=saved_at,
    )
    summary = RunSummary(source.id, documents_seen=1, detail={"by_hand": True})
    run_id = sink.start_run(source, RUNNER)
    try:
        doc = archive(result, source, store, {"by_hand": True})
        summary.documents_new = int(sink.save_document(doc))
        summary.status = "ok"
    except Exception as exc:
        summary.status = "failed"
        summary.error = repr(exc)
        raise
    finally:
        sink.finish_run(run_id, summary)
    return summary


def check(
    source: Source, path: Path, saved_at: dt.datetime, *, now: dt.datetime | None = None
) -> tuple[str, bytes]:
    """The page's address and the file's bytes. Raises NotStored. Touches no database."""
    if not source.hand_saved or source.id not in REGISTRY:
        raise NotStored(
            f"{source.id} is not marked hand_saved in config/sources.yaml. Only a source the "
            "owner has marked takes a page saved by hand."
        )
    if saved_at.tzinfo is None:
        raise NotStored("the time needs a time zone, such as 2026-11-24T15:30:00-06:00")
    if saved_at > (now or dt.datetime.now(dt.UTC)):
        raise NotStored(f"the time {saved_at.isoformat()} is in the future")
    body = path.read_bytes()
    try:
        url = REGISTRY[source.id]().saved_page(body)
    except (LayoutChanged, NotImplementedError) as exc:
        raise NotStored(
            f"{path.name} is not the page of {source.id}: {exc}. Save the page as "
            '"Webpage, HTML only" and try again. Nothing was stored.'
        ) from exc
    return url, body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Store a page a person saved in a browser.")
    parser.add_argument("source_id", help="the id in config/sources.yaml")
    parser.add_argument("file", type=Path, help="the saved page")
    parser.add_argument(
        "--saved-at",
        type=dt.datetime.fromisoformat,
        default=None,
        metavar="TIME",
        help="when the page was saved, with a time zone. Default: the file's own time",
    )
    args = parser.parse_args(argv)

    database_url = os.environ.get("DATABASE_URL")
    archive_dir = os.environ.get("RADAR_ARCHIVE_DIR")
    if not database_url or not archive_dir:
        print("not started: set DATABASE_URL and RADAR_ARCHIVE_DIR", file=sys.stderr)
        return 2
    try:
        source = load_sources().by_id(args.source_id)
    except KeyError:
        print(f"no source with id {args.source_id} in config/sources.yaml", file=sys.stderr)
        return 2
    if not args.file.is_file():
        print(f"no file at {args.file}", file=sys.stderr)
        return 2
    saved_at = args.saved_at or file_time(args.file)
    try:
        check(source, args.file, saved_at)  # before the database is opened
        with psycopg.connect(database_url, autocommit=True) as conn:
            summary = store_saved_page(
                source=source,
                path=args.file,
                saved_at=saved_at,
                store=LocalArchive(Path(archive_dir)),
                sink=PostgresSink(conn),
            )
    except NotStored as exc:
        print(f"not stored: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({**dataclasses.asdict(summary), "saved_at": saved_at.isoformat()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
