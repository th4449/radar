"""The backup command and its restore trial. Written before the code.

A dump of the database holds subscribers' addresses and reviewers' records. The repository is
public, so the command refuses to write one inside it. No test here touches a database.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("backup", REPO / "scripts/backup.py")
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


def test_a_dump_is_never_written_inside_the_repository(tmp_path):
    for inside in (REPO, REPO / "dumps", REPO / "web" / "dist"):
        with pytest.raises(backup.Refused, match="public"):
            backup.safe_folder(inside)
    assert backup.safe_folder(tmp_path) == tmp_path.resolve()


def test_a_dump_file_is_named_for_the_day_and_hour_it_was_made(tmp_path):
    import datetime as dt

    when = dt.datetime(2026, 12, 1, 14, 5, tzinfo=dt.UTC)
    assert backup.dump_path(tmp_path, when).name == "radar-2026-12-01T1405Z.dump"


def test_the_trial_restores_only_into_a_server_on_this_computer():
    assert backup.local_server("postgresql://postgres:x@127.0.0.1:55322/postgres")
    assert backup.local_server("postgresql://postgres:x@localhost:5432/postgres")
    for remote in (
        "postgresql://postgres:x@db.example.supabase.co:5432/postgres",
        "postgresql://postgres:x@10.0.0.5:5432/postgres",
    ):
        with pytest.raises(backup.Refused, match="this computer"):
            backup.local_server(remote)


def test_a_program_in_a_container_reaches_this_computer_by_its_other_name():
    here = "postgresql://postgres:x@127.0.0.1:55322/radar_backtest"
    assert backup.from_a_container(here) == (
        "postgresql://postgres:x@host.docker.internal:55322/radar_backtest"
    )
    away = "postgresql://postgres:x@db.example.supabase.co:5432/postgres"
    assert backup.from_a_container(away) == away


def test_a_restore_passes_only_when_every_table_came_back_whole():
    before = {"documents": 5918, "sources": 6, "signals": 0}
    assert backup.compare(before, dict(before)) == []
    assert backup.compare(before, {"documents": 5917, "sources": 6, "signals": 0}) == [
        "documents: 5918 rows dumped, 5917 restored"
    ]
    assert backup.compare(before, {"documents": 5918, "sources": 6}) == [
        "signals: 0 rows dumped, table missing after the restore"
    ]


def test_the_address_of_the_database_is_never_in_a_command_line():
    url = "postgresql://postgres:secret-word@db.example.supabase.co:5432/postgres"
    command, env = backup.dump_command(url, "postgres:17")
    assert "secret-word" not in " ".join(command)
    assert env["RADAR_DUMP_URL"] == url
