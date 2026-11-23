"""The monitor reads the run log as the database holds it."""

from __future__ import annotations

import datetime as dt

import pytest

from collectors.base import RunSummary
from pipeline import health
from pipeline.store import PostgresSink

from ..helpers import make_source
from .conftest import as_service

pytestmark = pytest.mark.db


def test_the_log_is_read_newest_runs_first_and_judged(db):
    source = make_source()
    with as_service(db):
        sink = PostgresSink(db)
        first = sink.start_run(source, runner="gha-1")
        sink.finish_run(first, RunSummary("tx_example", "ok", 3, 1, 0, None, {}))
        second = sink.start_run(source, runner="gha-2")
        sink.finish_run(
            second, RunSummary("tx_example", "blocked", 0, 0, 0, "robots.txt does not allow", {})
        )
        runs = health.load_runs(db)
        steps = health.load_steps(db)
    assert sorted(r.status for r in runs) == ["blocked", "ok"]
    assert {r.source_id for r in runs} == {"tx_example"}
    (found,) = health.check([source], runs, dt.datetime.now(dt.UTC))
    assert found.state == "blocked" and found.needs_a_person
    assert health.check_processing(steps, dt.datetime.now(dt.UTC)).state == "never_run"
