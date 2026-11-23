"""Back up the database, and prove a backup can be restored. BUILD_PLAN.md milestone M10.

    uv run python scripts/backup.py dump <a folder outside the repository>
    uv run python scripts/backup.py trial <the dump file>

`dump` needs DATABASE_URL. It writes one file with everything in the radar's own schemas, and
beside it the number of rows in each table on that day.

`trial` needs TRIAL_DATABASE_URL: any database on a Postgres server **on this computer**. It
makes a scratch database there with the map extension the radar's schema needs, restores the
dump into it, counts the rows of every table against the numbers written at the dump, and
drops the scratch database. A backup nobody has
restored is a hope, not a backup.

**A dump holds subscribers' addresses and reviewers' records.** This repository is public.
The command refuses to write a dump inside it. Keep dumps somewhere private, and never upload
one as a workflow artifact: an artifact of a public repository can be downloaded by others.

The dump and the restore run inside a container, so the tools match the server's version
whatever is installed on this computer. `--image` names the image, `postgres:17` by default.
The address of the database is handed over in the environment, never on a command line.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg import sql

REPO = Path(__file__).resolve().parent.parent
SCHEMAS = ("public", "private")
# What the radar's own migrations ask the server for before any table is made. A scratch
# database is given the same, or the tables that lean on it cannot be restored.
PREPARE = (
    "create schema if not exists extensions",
    "create extension if not exists postgis with schema extensions",
)
IMAGE = "postgres:17"
LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")


class Refused(Exception):
    """The command will not do this."""


def safe_folder(folder: Path) -> Path:
    folder = Path(folder).expanduser().resolve()
    if folder == REPO or REPO in folder.parents:
        raise Refused(
            f"{folder} is inside the repository, which is public. A dump holds subscribers' "
            "addresses. Name a folder somewhere private."
        )
    return folder


def dump_path(folder: Path, when: dt.datetime) -> Path:
    return folder / f"radar-{when:%Y-%m-%dT%H%MZ}.dump"


def local_server(url: str) -> bool:
    host = urlsplit(url).hostname or ""
    if host not in LOCAL_HOSTS:
        raise Refused(f"the restore trial writes only to a server on this computer, not to {host}")
    return True


def from_a_container(url: str) -> str:
    """The same address as a program inside a container on this computer must write it."""
    parts = urlsplit(url)
    if (parts.hostname or "") not in LOCAL_HOSTS:
        return url
    netloc = parts.netloc.replace(parts.hostname, "host.docker.internal")
    return urlunsplit(parts._replace(netloc=netloc))


def dump_command(url: str, image: str) -> tuple[list[str], dict[str, str]]:
    schemas = " ".join(f"--schema={name}" for name in SCHEMAS)
    inner = f'pg_dump "$RADAR_DUMP_URL" --format=custom --no-owner --no-privileges {schemas}'
    command = ["docker", "run", "--rm", "-e", "RADAR_DUMP_URL", image, "sh", "-c", inner]
    return command, {**os.environ, "RADAR_DUMP_URL": url}


def restore_command(url: str, image: str) -> tuple[list[str], dict[str, str]]:
    inner = 'pg_restore --dbname="$RADAR_DUMP_URL" --no-owner --no-privileges'
    command = ["docker", "run", "--rm", "-i", "-e", "RADAR_DUMP_URL", image, "sh", "-c", inner]
    return command, {**os.environ, "RADAR_DUMP_URL": url}


def row_counts(url: str) -> dict[str, int]:
    """The number of rows in every table of the public schema."""
    with psycopg.connect(url) as conn:
        tables = [
            row[0]
            for row in conn.execute(
                "select tablename from pg_tables where schemaname = 'public' order by 1"
            )
        ]
        count = sql.SQL("select count(*) from {}.{}")
        return {
            name: conn.execute(
                count.format(sql.Identifier("public"), sql.Identifier(name))
            ).fetchone()[0]
            for name in tables
        }


def compare(before: dict[str, int], after: dict[str, int]) -> list[str]:
    """What did not come back whole. Empty when everything did."""
    problems = []
    for name, rows in sorted(before.items()):
        if name not in after:
            problems.append(f"{name}: {rows} rows dumped, table missing after the restore")
        elif after[name] != rows:
            problems.append(f"{name}: {rows} rows dumped, {after[name]} restored")
    return problems


def dump(folder: Path, url: str, image: str) -> Path:
    folder = safe_folder(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = dump_path(folder, dt.datetime.now(dt.UTC))
    counts = row_counts(url)
    command, env = dump_command(from_a_container(url), image)
    with path.open("wb") as out:
        # The command is built here from fixed words and the image the caller named.
        done = subprocess.run(  # noqa: S603
            command, env=env, stdout=out, stderr=subprocess.PIPE, check=False
        )
    if done.returncode != 0 or path.stat().st_size == 0:
        path.unlink(missing_ok=True)
        raise Refused(f"the dump failed: {done.stderr.decode(errors='replace')[-400:]}")
    path.with_suffix(".counts.json").write_text(json.dumps(counts, indent=1) + "\n")
    return path


def trial(path: Path, server_url: str, image: str) -> list[str]:
    local_server(server_url)
    before = json.loads(path.with_suffix(".counts.json").read_text())
    scratch = f"radar_restore_trial_{dt.datetime.now(dt.UTC):%Y%m%d%H%M%S}"
    parts = urlsplit(server_url)
    scratch_url = urlunsplit(parts._replace(path=f"/{scratch}"))
    with psycopg.connect(server_url, autocommit=True) as conn:
        conn.execute(sql.SQL("create database {}").format(sql.Identifier(scratch)))
    try:
        with psycopg.connect(scratch_url, autocommit=True) as conn:
            for statement in PREPARE:
                conn.execute(statement)
        command, env = restore_command(from_a_container(scratch_url), image)
        with path.open("rb") as source:
            subprocess.run(  # noqa: S603
                command, env=env, stdin=source, capture_output=True, check=False
            )
        # A restore into a bare database reports errors for what the hosted service owns,
        # such as the sign-in tables other tables point at. The rows are what is judged.
        return compare(before, row_counts(scratch_url))
    finally:
        with psycopg.connect(server_url, autocommit=True) as conn:
            conn.execute(
                sql.SQL("drop database if exists {} with (force)").format(sql.Identifier(scratch))
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Back up the database and try a restore.")
    parser.add_argument("--image", default=IMAGE, help="the container image with the tools")
    steps = parser.add_subparsers(dest="step", required=True)
    steps.add_parser("dump").add_argument("folder", type=Path)
    steps.add_parser("trial").add_argument("file", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.step == "dump":
            url = os.environ.get("DATABASE_URL")
            if not url:
                print("not started: set DATABASE_URL", file=sys.stderr)
                return 2
            path = dump(args.folder, url, args.image)
            print(f"wrote {path} ({path.stat().st_size:,} bytes) and its row counts")
            return 0
        url = os.environ.get("TRIAL_DATABASE_URL")
        if not url:
            print("not started: set TRIAL_DATABASE_URL to a server on this computer",
                  file=sys.stderr)  # fmt: skip
            return 2
        problems = trial(args.file, url, args.image)
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    if problems:
        print("THE RESTORE DID NOT COME BACK WHOLE:\n  " + "\n  ".join(problems))
        return 1
    print("The restore came back whole: every table has the rows it had at the dump.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
