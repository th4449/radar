"""The command that runs one collector."""

from __future__ import annotations

import re
from pathlib import Path

import httpx
import pytest

from collectors import run as runner
from pipeline.config import load_sources

from .helpers import CONTACT, FakeClock, Site
from .test_tx_comptroller_data_centers import BODY, ROBOTS, URL
from .test_tx_comptroller_data_centers import source as lists_when_a_job_read_it


def test_every_source_cleared_for_fetching_has_a_collector_and_no_other_does():
    # A lookup service is queried by the pipeline, one record at a time. It has no collector.
    cleared = {
        s.id for s in load_sources().sources if s.may_fetch_automatically and s.layer != "lookup"
    }
    # A source a person saves by hand keeps its collector: the saved page goes through it.
    by_hand = {s.id for s in load_sources().sources if s.hand_saved}
    assert cleared | by_hand == set(runner.REGISTRY)
    assert not cleared & by_hand
    for source_id, collector in runner.REGISTRY.items():
        assert collector.source_id == source_id


def test_a_source_saved_by_hand_does_not_start_and_the_refusal_says_what_to_do():
    lists = load_sources().by_id("tx_comptroller_data_centers")
    with pytest.raises(runner.CannotStart, match="collectors.by_hand"):
        runner.run_source(lists, dry_run=True, contact=CONTACT)


def test_a_dry_run_fetches_and_keeps_nothing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    web = Site({URL: httpx.Response(200, content=BODY)}, robots=ROBOTS)
    clock = FakeClock()
    summary = runner.run_source(
        lists_when_a_job_read_it(),
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
            lists_when_a_job_read_it(),
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


WORKFLOWS = Path(__file__).parents[1] / ".github" / "workflows"
# What a schedule line looks like for each cadence: minute, hour, day of month, month, weekday.
CRON_FOR = {
    "daily": re.compile(r"^(\d{1,2}) (\d{1,2}) \* \* \*$"),
    "weekly": re.compile(r"^(\d{1,2}) (\d{1,2}) \* \* [0-6]$"),
    "monthly": re.compile(r"^(\d{1,2}) (\d{1,2}) ([1-9]|1\d|2[0-8]) \* \*$"),
}


def crons(name: str) -> list[str]:
    """The schedule lines of a workflow file."""
    return re.findall(r'^\s+- cron: "([^"]+)"$', (WORKFLOWS / name).read_text(), re.M)


def minute_of_day(cron: str) -> int:
    minute, hour = cron.split()[:2]
    return int(hour) * 60 + int(minute)


def collector_workflows() -> dict[str, str]:
    """Each automated source and its workflow file."""
    sources = load_sources()
    return {
        source_id: f"collect-{source_id.replace('_', '-')}.yml"
        for source_id in runner.REGISTRY
        if not sources.by_id(source_id).hand_saved
    }


def test_every_collector_has_a_workflow_file_scheduled_at_its_sources_cadence():
    """The owner gave the go-ahead for schedules on November 27, 2026. Each collector runs at
    the cadence its source has in config/sources.yaml, and can still be started by hand."""
    sources = load_sources()
    for source_id in runner.REGISTRY:
        path = WORKFLOWS / f"collect-{source_id.replace('_', '-')}.yml"
        if sources.by_id(source_id).hand_saved:
            assert not path.exists()  # no job reads it, so no workflow offers to
            continue
        text = path.read_text()
        assert f"source_id: {source_id}" in text
        assert "workflow_dispatch:" in text
        (cron,) = crons(path.name)  # one schedule line, no more
        cadence = sources.by_id(source_id).cadence
        assert CRON_FOR[cadence].match(cron), f"{path.name}: {cron} is not {cadence}"
        assert not cron.startswith("0 "), "the top of the hour is when GitHub is busiest"
    shared = (WORKFLOWS / "collect.yml").read_text()
    assert "--dry-run" in shared and "schedule:" not in shared


def test_no_two_collectors_start_at_the_same_minute():
    # Two collectors read the same site, ERCOT's. Each paces itself, not the other.
    starts = [minute_of_day(crons(name)[0]) for name in collector_workflows().values()]
    assert len(set(starts)) == len(starts)
    assert min(abs(a - b) for a in starts for b in starts if a != b) >= 5


def test_processing_runs_each_day_after_every_collector_and_the_monitor_after_that():
    (process,) = crons("process.yml")
    (monitor,) = crons("monitor.yml")
    assert CRON_FOR["daily"].match(process) and CRON_FOR["daily"].match(monitor)
    last_collector = max(minute_of_day(crons(n)[0]) for n in collector_workflows().values())
    # The longest collector is stopped at 90 minutes. Processing waits that long and more.
    assert minute_of_day(process) - last_collector >= 100
    # Processing is stopped at 60 minutes.
    assert minute_of_day(monitor) - minute_of_day(process) >= 60


def test_what_is_never_scheduled():
    """The policy tests write to the hosted database and roll back. They run on the owner's
    word each time. The email job waits for the owner's decision on real email."""
    for name in ("policy-tests.yml", "email.yml", "collect.yml"):
        text = (WORKFLOWS / name).read_text()
        assert "schedule:" not in text and "cron:" not in text, name


def test_a_workflow_keeps_nothing_unless_the_owner_has_switched_real_runs_on():
    """A real run writes to the hosted database. That is the owner's decision, given by a
    repository variable and secrets that no commit can set."""
    workflows = Path(__file__).parents[1] / ".github" / "workflows"
    shared = (workflows / "collect.yml").read_text()
    assert 'if [ "$RADAR_LIVE" = "true" ]; then' in shared
    live, dry = shared.split('if [ "$RADAR_LIVE" = "true" ]; then')[1].split("else")
    assert "--dry-run" not in live and "--dry-run" in dry
    process = (workflows / "process.yml").read_text()
    assert 'if [ "$RADAR_LIVE" != "true" ]; then' in process and "exit 0" in process
    email = (workflows / "email.yml").read_text()
    live, dry = email.split('if [ "$RADAR_EMAIL_LIVE" = "true" ]; then')[1].split("else")
    assert "--send" in live and "--send" not in dry
    for name in ("collect.yml", "process.yml", "monitor.yml", "email.yml"):
        text = (workflows / name).read_text()
        # Addresses and keys come from the repository's settings, never from the file.
        assert "postgresql://" not in text and "supabase.co" not in text, name
        assert "secrets.RADAR_DATABASE_URL" in text, name
    # A caller hands the shared steps the secrets a real run reads.
    for source_id in runner.REGISTRY:
        path = workflows / f"collect-{source_id.replace('_', '-')}.yml"
        if path.exists():
            assert "secrets: inherit" in path.read_text(), path.name


# --- a one-time history run, for the backtest ----------------------------------------------------


def test_a_history_run_is_refused_for_a_collector_that_has_no_history_setting():
    import datetime as dt

    lists = lists_when_a_job_read_it()
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
