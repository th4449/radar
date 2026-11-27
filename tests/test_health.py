"""Monitoring for failed collectors. BUILD_PLAN.md milestone M10. Written before the code.

Every run is logged, success or failure. This reads the log and says which sources need a
person: a run that failed, a site that refused, a source nobody has read for too long, a page
a person is due to save by hand. Every source and run here is made up.
"""

from __future__ import annotations

import datetime as dt

import pytest

from pipeline import health
from pipeline.config import Source

NOW = dt.datetime(2027, 1, 15, 12, 0, tzinfo=dt.UTC)


def source(source_id: str = "tx_example", cadence: str = "weekly", **changes) -> Source:
    base = {
        "id": source_id,
        "state": "TX",
        "name": "Example feed",
        "url": "https://example.gov/feed",
        "layer": "signal",
        "method": "http",
        "intended_method": "http",
        "cadence": cadence,
        "robots_status": "allowed",
        "verified_at": dt.date(2026, 11, 19),
        "notes": "",
    }
    return Source(**{**base, **changes})


def run(days_ago: float, status: str = "ok", source_id: str = "tx_example", **more) -> health.Run:
    started = NOW - dt.timedelta(days=days_ago)
    finished = None if status == "running" else started + dt.timedelta(minutes=5)
    values = {"documents_seen": 3, "documents_new": 1, "errors": 0, "error": None, **more}
    return health.Run(source_id, started, finished, status, **values)


def one(sources, runs) -> health.Health:
    (found,) = health.check(sources, runs, NOW)
    return found


def test_a_source_read_cleanly_and_on_time_needs_nobody():
    found = one([source()], [run(1), run(8)])
    assert found.state == "ok" and not found.needs_a_person
    assert found.last_ok == NOW - dt.timedelta(days=1) + dt.timedelta(minutes=5)


def test_a_source_with_no_run_at_all_is_said_to_have_none():
    found = one([source()], [])
    assert found.state == "never_run" and found.needs_a_person


def test_a_failed_run_needs_a_person_and_says_how_many_in_a_row():
    runs = [run(1, "failed", error="layout changed"), run(2, "partial", errors=2), run(9)]
    found = one([source()], runs)
    assert found.state == "failing" and found.needs_a_person
    assert "2 runs in a row" in found.note and "layout changed" in found.note
    assert found.last_ok == NOW - dt.timedelta(days=9) + dt.timedelta(minutes=5)


def test_a_refusal_is_its_own_state_and_says_not_to_ask_again():
    found = one([source()], [run(1, "blocked", error="robots.txt does not allow it"), run(8)])
    assert found.state == "blocked" and found.needs_a_person
    assert "Do not run it again" in found.note


@pytest.mark.parametrize(
    ("cadence", "days_ago", "state"),
    [
        ("daily", 1.5, "ok"),
        ("daily", 3, "stale"),
        ("weekly", 8, "ok"),
        ("weekly", 10, "stale"),
        ("monthly", 34, "ok"),
        ("monthly", 36, "stale"),
        ("yearly", 380, "ok"),
        ("once", 900, "ok"),
        ("on_demand", 900, "ok"),
    ],
)
def test_a_source_nobody_has_read_within_its_cadence_is_stale(cadence, days_ago, state):
    found = one([source(cadence=cadence)], [run(days_ago)])
    assert found.state == state
    assert found.needs_a_person == (state != "ok")


def test_a_run_that_started_and_never_finished_is_stuck():
    found = one([source()], [run(0.5, "running"), run(7)])
    assert found.state == "stuck" and found.needs_a_person
    # A run that started a few minutes ago is just running.
    assert one([source()], [run(0.01, "running"), run(7)]).state == "ok"


def test_a_page_a_person_saves_is_due_when_its_last_copy_is_old():
    lists = source(
        "tx_example_list", "monthly", method="manual", robots_status="blocked", hand_saved=True
    )
    fresh = one([lists], [run(20, source_id="tx_example_list")])
    assert fresh.state == "ok"
    due = one([lists], [run(40, source_id="tx_example_list")])
    assert due.state == "due_by_hand" and due.needs_a_person
    assert "collectors.by_hand" in due.note
    never = one([lists], [])
    assert never.state == "due_by_hand"


def test_a_source_no_job_reads_and_nobody_saves_is_not_watched():
    held = source("tx_example_held", method="manual", robots_status="restricted")
    lookup = source("tx_example_lookup", layer="lookup")
    assert health.check([held, lookup], [], NOW) == []


def test_the_ones_that_need_a_person_come_first():
    sources = [source("tx_a"), source("tx_b"), source("tx_c")]
    runs = [run(1, source_id="tx_a"), run(1, "failed", source_id="tx_b", error="x")]
    found = health.check(sources, runs, NOW)
    assert [h.source_id for h in found] == ["tx_b", "tx_c", "tx_a"]
    assert [h.needs_a_person for h in found] == [True, True, False]


# --- processing ----------------------------------------------------------------------------------


def step(days_ago: float, status: str = "ok", **more) -> health.Step:
    started = NOW - dt.timedelta(days=days_ago)
    finished = None if status == "running" else started + dt.timedelta(minutes=2)
    return health.Step(started, finished, status, **{"errors": 0, "error": None, **more})


def test_processing_is_watched_the_same_way():
    assert health.check_processing([step(0.5)], NOW).state == "ok"
    assert health.check_processing([], NOW).state == "never_run"
    failing = health.check_processing(
        [step(0.5, "partial", errors=3, error="document 7"), step(2)], NOW
    )
    assert failing.state == "failing" and "document 7" in failing.note
    assert health.check_processing([step(3)], NOW).state == "stale"


# --- what a person reads -------------------------------------------------------------------------


def test_the_report_puts_what_needs_a_person_first_and_names_no_address():
    sources = [source("tx_a"), source("tx_b")]
    found = health.check(
        sources, [run(1, source_id="tx_a"), run(1, "blocked", source_id="tx_b")], NOW
    )
    text = health.report(found, health.check_processing([step(0.5)], NOW), NOW)
    assert text.index("tx_b") < text.index("tx_a")
    assert "1 of 2 sources need a person" in text
    assert "@" not in text


# --- the workflow --------------------------------------------------------------------------------


def test_the_monitor_workflow_runs_each_day_and_sends_nothing():
    from pathlib import Path

    text = (Path(__file__).parents[1] / ".github" / "workflows" / "monitor.yml").read_text()
    assert "workflow_dispatch:" in text and "python -m pipeline.health" in text
    # Once a day, on the owner's go-ahead of November 27, 2026. tests/test_run_cli.py holds
    # that it comes after the collectors and processing.
    assert text.count("- cron:") == 1
    # The address of the database is a secret, never written into the file.
    assert "secrets.RADAR_DATABASE_URL" in text and "postgresql://" not in text


def test_the_runbook_says_what_to_do_for_every_state():
    from pathlib import Path

    runbook = (Path(__file__).parents[1] / "docs" / "runbook.md").read_text()
    states = ("ok", "failing", "blocked", "stuck", "stale", "never_run", "due_by_hand")
    for state in states:
        assert f"| `{state}` |" in runbook, state
    # And the monitor gives no state the runbook does not know.
    sources = [source("tx_a")]
    for runs in ([], [run(1)], [run(1, "failed")], [run(1, "blocked")], [run(1, "running")]):
        assert one(sources, runs).state in states
