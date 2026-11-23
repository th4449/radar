"""The command that runs one collector."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from collectors import run as runner
from pipeline.config import load_sources

from .helpers import CONTACT, FakeClock, Site
from .test_tx_comptroller_data_centers import BODY, ROBOTS, URL


def test_every_source_cleared_for_fetching_has_a_collector_and_no_other_does():
    # A lookup service is queried by the pipeline, one record at a time. It has no collector.
    cleared = {
        s.id for s in load_sources().sources if s.may_fetch_automatically and s.layer != "lookup"
    }
    assert cleared == set(runner.REGISTRY)
    for source_id, collector in runner.REGISTRY.items():
        assert collector.source_id == source_id


def test_a_dry_run_fetches_and_keeps_nothing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    web = Site({URL: httpx.Response(200, content=BODY)}, robots=ROBOTS)
    clock = FakeClock()
    summary = runner.run_source(
        load_sources().by_id("tx_comptroller_data_centers"),
        dry_run=True,
        contact=CONTACT,
        transport=web.transport,
        clock=clock,
        sleep=clock.sleep,
    )
    assert (summary.status, summary.documents_new) == ("ok", 1)
    assert web.page_urls() == [URL]


def test_a_manual_source_does_not_start():
    manual = load_sources().by_id("tx_public_notices")
    with pytest.raises(runner.CannotStart, match="no collector"):
        runner.run_source(manual, dry_run=True, contact=CONTACT)


def test_a_real_run_needs_a_database_and_an_archive(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("RADAR_ARCHIVE_DIR", raising=False)
    web = Site({URL: httpx.Response(200, content=BODY)}, robots=ROBOTS)
    with pytest.raises(runner.CannotStart, match="DATABASE_URL"):
        runner.run_source(
            load_sources().by_id("tx_comptroller_data_centers"),
            dry_run=False,
            contact=CONTACT,
            transport=web.transport,
        )
    assert web.requests == []


def test_command_line_exit_codes(capsys, monkeypatch):
    monkeypatch.setenv("RADAR_CONTACT", CONTACT)
    assert runner.main(["tx_no_such_source", "--dry-run"]) == 2
    assert "no source with id" in capsys.readouterr().err
    assert runner.main(["tx_public_notices", "--dry-run"]) == 2
    assert "not started" in capsys.readouterr().err


def test_every_collector_has_a_workflow_file_that_is_not_scheduled():
    workflows = Path(__file__).parents[1] / ".github" / "workflows"
    for source_id in runner.REGISTRY:
        text = (workflows / f"collect-{source_id.replace('_', '-')}.yml").read_text()
        assert f"source_id: {source_id}" in text
        assert "workflow_dispatch:" in text
        # A schedule is a launch decision. It needs the owner's go-ahead.
        assert "schedule:" not in text and "cron" not in text
    shared = (workflows / "collect.yml").read_text()
    assert "--dry-run" in shared


# --- a one-time history run, for the backtest ----------------------------------------------------


def test_a_history_run_is_refused_for_a_collector_that_has_no_history_setting():
    import datetime as dt

    lists = load_sources().by_id("tx_comptroller_data_centers")
    with pytest.raises(runner.CannotStart, match="no history"):
        runner.run_source(lists, dry_run=True, contact=CONTACT, history_since=dt.date(2023, 1, 1))


def test_the_command_reads_the_first_day_of_a_history_run(monkeypatch):
    import datetime as dt

    seen = {}

    def stand_in(source, **kwargs):
        seen.update(kwargs, source=source.id)
        return runner.RunSummary(source.id, status="ok")

    monkeypatch.setattr(runner, "run_source", stand_in)
    assert runner.main(["tx_ercot_rpg", "--dry-run", "--history-since", "2023-01-01"]) == 0
    assert seen["history_since"] == dt.date(2023, 1, 1) and seen["dry_run"] is True
    assert runner.main(["tx_ercot_rpg", "--dry-run"]) == 0
    assert seen["history_since"] is None
