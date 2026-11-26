"""Count the rows of every table, and say whether a later count is the same.

    uv run python scripts/table_counts.py save <file>
    uv run python scripts/table_counts.py compare <file>

Both need DATABASE_URL. `save` writes the counts to the file. `compare` counts again and ends
with an error when any table has a different number of rows than the file says.

It is the check from outside on a run that must leave nothing: the policy tests on the hosted
database. See .github/workflows/policy-tests.yml and docs/launch_checklist.md. The tests roll
back what they write. This shows that they did.

It reads only. It prints table names and numbers, never a row. The file holds the same and
is safe to print, but it is not a thing to commit: write it outside the repository.

A count is not proof that no row changed. A test that changed a row and left the number of
rows alone would pass it. The tests' own rollback is the guard against that. This catches the
harm that matters most: an account, a reviewer or a record that was not there before.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql

# The radar's own schemas, the accounts and the list of archived files.
SCHEMAS = ("public", "private", "auth", "storage")


def counts(conn: psycopg.Connection) -> dict[str, int]:
    """The number of rows in every ordinary table of the counted schemas."""
    tables = conn.execute(
        """select n.nspname, c.relname from pg_class c
           join pg_namespace n on n.oid = c.relnamespace
           where n.nspname = any(%s) and c.relkind in ('r', 'p')
           order by 1, 2""",
        [list(SCHEMAS)],
    ).fetchall()
    out: dict[str, int] = {}
    for schema, table in tables:
        query = sql.SQL("select count(*) from {}.{}").format(
            sql.Identifier(schema), sql.Identifier(table)
        )
        out[f"{schema}.{table}"] = conn.execute(query).fetchone()[0]
    return out


def differences(before: dict[str, int], after: dict[str, int]) -> list[str]:
    """One line for each table whose count is not the same, in name order."""
    lines = []
    for name in sorted(set(before) | set(after)):
        was, now = before.get(name), after.get(name)
        if was != now:
            was_said = "not there before" if was is None else f"{was} before"
            now_said = "not there after" if now is None else f"{now} after"
            lines.append(f"{name}: {was_said}, {now_said}")
    return lines


def compare(saved: Path, after: dict[str, int]) -> int:
    before = json.loads(saved.read_text())
    found = differences(before, after)
    if not found:
        print(f"Nothing was left: {len(after)} tables, {sum(after.values())} rows, as before.")
        return 0
    print("A ROW WAS LEFT OR LOST. These tables do not hold what they held before:")
    for line in found:
        print(f"  {line}")
    print("If no other job ran meanwhile, a test kept something. Find it before any other run.")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Count every table, or compare with a count.")
    parser.add_argument("action", choices=("save", "compare"))
    parser.add_argument("file", type=Path)
    args = parser.parse_args(argv)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("not started: set DATABASE_URL", file=sys.stderr)
        return 2
    with psycopg.connect(database_url, connect_timeout=30) as conn:
        conn.execute("set transaction read only")
        now = counts(conn)
    if args.action == "save":
        args.file.write_text(json.dumps(now, indent=2, sort_keys=True))
        print(f"Counted {len(now)} tables, {sum(now.values())} rows.")
        return 0
    return compare(args.file, now)


if __name__ == "__main__":
    raise SystemExit(main())
