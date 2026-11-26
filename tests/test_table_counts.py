"""Counting every table before and after a run that must leave nothing. Written first.

The policy tests roll back what they write. On the hosted database that promise is checked
from outside: the rows of every table are counted before the tests and again after, and any
difference fails the job. No test here touches a database.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("table_counts", REPO / "scripts/table_counts.py")
table_counts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(table_counts)

BEFORE = {"auth.users": 0, "public.documents": 222, "public.reviewers": 0, "public.sites": 8}


def test_the_same_counts_are_no_difference():
    assert table_counts.differences(BEFORE, dict(BEFORE)) == []


def test_a_row_left_behind_is_named_with_both_counts():
    after = {**BEFORE, "auth.users": 1, "public.reviewers": 2}

    assert table_counts.differences(BEFORE, after) == [
        "auth.users: 0 before, 1 after",
        "public.reviewers: 0 before, 2 after",
    ]


def test_a_row_that_went_missing_counts_too():
    assert table_counts.differences(BEFORE, {**BEFORE, "public.sites": 7}) == [
        "public.sites: 8 before, 7 after"
    ]


def test_a_table_that_appeared_or_vanished_is_a_difference():
    after = {k: v for k, v in BEFORE.items() if k != "public.sites"} | {"public.new_table": 0}

    assert table_counts.differences(BEFORE, after) == [
        "public.new_table: not there before, 0 after",
        "public.sites: 8 before, not there after",
    ]


def test_comparing_passes_on_the_same_counts_and_fails_on_any_other(tmp_path, capsys):
    saved = tmp_path / "before.json"
    saved.write_text(json.dumps(BEFORE))

    assert table_counts.compare(saved, dict(BEFORE)) == 0
    assert "Nothing was left" in capsys.readouterr().out

    assert table_counts.compare(saved, {**BEFORE, "auth.users": 1}) == 1
    said = capsys.readouterr().out
    assert "auth.users: 0 before, 1 after" in said
    assert "A ROW WAS LEFT OR LOST" in said


def test_the_counted_schemas_are_the_radars_own_and_the_accounts():
    # A fake account or a fake reviewer is the harm to look for, so auth is counted with the
    # radar's own schemas. So is storage, where the archive's files are listed.
    assert table_counts.SCHEMAS == ("public", "private", "auth", "storage")


def test_the_command_does_not_start_without_a_database(monkeypatch, capsys):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert table_counts.main(["save", "anywhere.json"]) == 2
    assert "DATABASE_URL" in capsys.readouterr().err


def test_the_command_takes_only_save_and_compare():
    with pytest.raises(SystemExit):
        table_counts.main(["drop", "x.json"])
