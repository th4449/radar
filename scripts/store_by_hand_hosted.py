"""Store a page a person saved in a browser, in the hosted project. docs/runbook.md.

    uv run python scripts/store_by_hand_hosted.py tx_comptroller_data_centers \\
        ~/Downloads/data-center-lists.html

`collectors.by_hand` stores a saved page and needs the hosted database's address and the
archive's key. Both are secrets that live on GitHub and on no person's machine. This puts them
together for one command and keeps them in memory only:

- **The database password** is asked for at a prompt that shows nothing. It is the password
  set in the Supabase dashboard, the one the GitHub secret RADAR_DATABASE_URL holds. This
  command does not choose or change it.
- **The archive's key** is read from Supabase's own tool, which the person is signed in to.
- **Which project** is read from this checkout's link to it, in `supabase/.temp/`, a folder
  git ignores. `supabase link` makes it.

Neither secret is printed, logged or written to a file, and neither is left in the shell
afterwards. The command makes no request to the source's site: it stores a file a person
saved. The file is checked first, before anything is asked for, and a file that is not the
page is refused.

The exit code is the storing command's own: 0 when the page is stored or was stored before
and 1 when the file is refused. It is 2 when this command could not start.

The key it reads is the project's older service key. Supabase has said it will retire that
kind of key in early 2027. This command then needs another way to be given the key.
"""

from __future__ import annotations

import argparse
import datetime as dt
import getpass
import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple
from urllib.parse import quote, urlsplit

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:  # run as a file, the repository is not on the path
    sys.path.insert(0, str(REPO))

import psycopg  # noqa: E402

from collectors import by_hand  # noqa: E402
from pipeline.config import load_sources  # noqa: E402

TEMP = REPO / "supabase" / ".temp"
SETTINGS = ("DATABASE_URL", "RADAR_ARCHIVE_URL", "RADAR_ARCHIVE_KEY", "RADAR_ARCHIVE_DIR")


class CannotStart(Exception):
    """The command has not got what it needs. Nothing was stored."""


class Linked(NamedTuple):
    ref: str
    pooler: str


def linked_project(temp: Path = TEMP) -> Linked:
    """The hosted project this checkout is linked to, and the address of its session pooler."""
    try:
        ref = (temp / "project-ref").read_text().strip()
        pooler = (temp / "pooler-url").read_text().strip()
    except OSError:
        ref = pooler = ""
    if not ref or not pooler:
        raise CannotStart(
            "this checkout is not linked to the hosted project. Run `supabase link` first."
        )
    return Linked(ref, pooler)


def database_url(pooler: str, password: str) -> str:
    """The pooler's address with the password in it. Any password already there is dropped."""
    parts = urlsplit(pooler)
    if not parts.username or not parts.hostname:
        raise CannotStart("the saved pooler address has no user or no host. Run `supabase link`.")
    return (
        f"postgresql://{quote(parts.username, safe='.')}:{quote(password, safe='')}"
        f"@{parts.hostname}:{parts.port or 5432}{parts.path or '/postgres'}?sslmode=require"
    )


def service_key(listing: str) -> str:
    """The service key in the answer of `supabase projects api-keys -o json`."""
    try:
        rows = json.loads(listing)
    except ValueError:
        rows = None
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, dict) and row.get("name") == "service_role":
            key = row.get("api_key")
            # The tool shows some keys with their middle hidden. A hidden key is no key.
            if isinstance(key, str) and key and key.isascii() and key.isprintable():
                return key
    raise CannotStart("Supabase's tool did not give the project's service key.")


def _list_keys(ref: str) -> str:
    try:
        done = subprocess.run(  # noqa: S603
            ["supabase", "projects", "api-keys", "--project-ref", ref, "-o", "json"],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise CannotStart(f"Supabase's tool could not be run: {exc}") from exc
    if done.returncode != 0:
        raise CannotStart("Supabase's tool gave no keys. Sign in with `supabase login`.")
    return done.stdout


def _refusal(url: str) -> str | None:
    """None when the database takes the address. Otherwise the first line of why not."""
    try:
        with psycopg.connect(url, connect_timeout=30) as conn:
            conn.execute("select 1")
    except psycopg.OperationalError as exc:
        return (str(exc).strip().splitlines() or ["no reason given"])[0]
    return None


def main(
    argv: list[str] | None = None,
    *,
    ask: Callable[[str], str] = getpass.getpass,
    keys: Callable[[str], str] = _list_keys,
    connect: Callable[[str], str | None] = _refusal,
    store: Callable[[list[str]], int] = by_hand.main,
    temp: Path = TEMP,
) -> int:
    parser = argparse.ArgumentParser(
        description="Store a page a person saved in a browser, in the hosted project."
    )
    parser.add_argument("source_id", help="the id in config/sources.yaml")
    parser.add_argument("file", type=Path, help="the saved page")
    parser.add_argument("--saved-at", default=None, metavar="TIME")
    args = parser.parse_args(argv)

    # The file first. A file that is not the page is refused before any secret is asked for.
    try:
        source = load_sources().by_id(args.source_id)
    except KeyError:
        print(f"no source with id {args.source_id} in config/sources.yaml", file=sys.stderr)
        return 2
    if not args.file.is_file():
        print(f"no file at {args.file}", file=sys.stderr)
        return 2
    try:
        saved_at = (
            dt.datetime.fromisoformat(args.saved_at)
            if args.saved_at
            else by_hand.file_time(args.file)
        )
        by_hand.check(source, args.file, saved_at)
    except ValueError:
        print(f"not stored: {args.saved_at} is not a time", file=sys.stderr)
        return 1
    except by_hand.NotStored as exc:
        print(f"not stored: {exc}", file=sys.stderr)
        return 1

    try:
        project = linked_project(temp)
        print("The file is the page. This stores it in the hosted project.")
        print("Give the database password set in the Supabase dashboard. This does not")
        print("choose or change it.")
        password = ask("Database password (it will not show): ").strip()
        if not password:
            raise CannotStart("no password was given.")
        if not password.isascii() or not password.isprintable():
            raise CannotStart(
                "what arrived holds characters that are not plain keyboard characters. "
                "A paste can add them. Type it or paste it again."
            )
        url = database_url(project.pooler, password)
        refusal = connect(url)
        if refusal is not None:
            refusal = refusal.replace(password, "[hidden]").replace(project.ref, "[project]")
            raise CannotStart(f"the database did not take it: {refusal}")
        key = service_key(keys(project.ref))
    except CannotStart as exc:
        print(f"Not started: {exc}")
        print("Nothing was stored.")
        return 2

    before = {name: os.environ.get(name) for name in SETTINGS}
    os.environ["DATABASE_URL"] = url
    os.environ["RADAR_ARCHIVE_URL"] = f"https://{project.ref}.supabase.co"
    os.environ["RADAR_ARCHIVE_KEY"] = key
    os.environ.pop("RADAR_ARCHIVE_DIR", None)  # a local folder as well would be two archives
    try:
        passed = [args.source_id, str(args.file)]
        if args.saved_at:
            passed += ["--saved-at", args.saved_at]
        return store(passed)
    finally:
        for name, value in before.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


if __name__ == "__main__":
    raise SystemExit(main())
