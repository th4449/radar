"""The backtest report, written from made-up history. No real project is named here."""

from __future__ import annotations

import datetime as dt

from backtest.harness import run, sweep
from backtest.history import History, Meeting, harness_projects, history_rules, read
from backtest.report import coverage, write
from pipeline.config import Thresholds, load_scoring

from .test_backtest_history import agenda_file, known, legistar, wells

RULES = history_rules(None)
MILAM = "48331"
RIVER = known("milam-example-river", "Milam", "Example River LLC", place="near Cameron")
QUIET = known("milam-example-quiet", "Milam", "Example Quiet LLC", place="Rockdale")
OLD = known("milam-example-old", "Milam", news_date=dt.date(2021, 5, 1))
UNDATED = known(
    "milam-example-undated", "Milam", news_date=None, news_outlet="", news_url="",
    news_read="none_found",
)  # fmt: skip
KNOWN = [RIVER, QUIET, OLD, UNDATED]


def made() -> History:
    return read(
        enumerate(
            [
                legistar("Tax abatement for Example River, LLC for a data center"),
                legistar("Hear a report on the Orion data center", event_id=42, date="2026-04-06",
                         published="2026-04-02T10:00:00"),
                agenda_file("2. Pay the bills."),
                wells({"OwnerName": "Stranger Data Center LLC", "DateSubmitted": "2026-03-01"}),
            ],
            1,
        ),
        RULES,
        KNOWN,
        {},
    )  # fmt: skip


def report(threshold: float = 40) -> str:
    history = made()
    scoring = load_scoring().model_copy(
        update={"thresholds": Thresholds(review_threshold=threshold)}
    )
    result = run(
        harness_projects(KNOWN, history),
        [s for s in history.signals if s.county_fips],
        scoring,
        control_fips={"48279"},
        history_starts=dt.date(2023, 1, 1),
    )
    return write(result, history, KNOWN, sweep(result, [5.0, 40.0]), control_names=["Lamb"])


def test_the_report_gives_the_hit_rate_the_misses_the_false_alarms_and_the_lead_time():
    text = report()
    assert "**0 of 2 judged projects reached the review threshold of 40" in text
    assert "**1 of 2 had any signal before the public date.**" in text
    assert "Median lead time over hits: none. There is no hit to measure." in text
    assert "False alarms in the 1 control counties: 0." in text
    assert "| undated | 1 |" in text and "| before_history | 1 |" in text
    assert "| no_signal | 1 |" in text and "| below_threshold | 1 |" in text


def test_at_a_bar_the_record_reaches_the_report_gives_the_hit_and_its_lead():
    text = report(threshold=3)
    assert "**1 of 2 judged projects reached the review threshold of 3" in text
    assert "Median lead time over hits: 88 days." in text
    assert "| hit | 1 |" in text


def test_a_project_tied_only_by_its_name_is_not_counted_as_the_radars_own_catch():
    text = report()
    assert "0 of those could have been tied to the project by the everyday radar" in text
    # The record says "data center", so it is held to its meeting and sits on a site.
    assert "1 of those 1 rest on a record that sits on a site under the everyday rules" in text
    assert '| one meeting\'s agenda that says "data center" | 1 |' in text


def test_the_report_lists_each_tied_signal_by_its_reference_and_the_name_found():
    text = report()
    assert "| 2026-03-05 | `milam-example-river` | agenda item or file |" in text
    assert "company Example River LLC" in text
    assert "+88" in text  # March 5 to June 1, 2026


def test_a_site_that_fits_no_known_project_is_never_named():
    text = report()
    assert "Stranger" not in text
    assert "| a company or coordinates | 1 |" in text


def test_a_record_that_says_data_center_and_is_tied_to_no_project_is_listed_for_a_person():
    text = report()
    # The agenda item, and the well report of a company the list of known projects lacks.
    assert '2 records that say "data center"' in text
    assert (
        "| Milam | 2026-03-01 | well report | Texas well report tracking number 9100001 |" in text
    )
    assert "| 2026-04-02 | agenda item or file | Example City Council, meeting of April 6" in text


def test_the_report_says_what_the_pending_permit_lists_can_and_cannot_show():
    text = report()
    assert "The two lists give 0 signals." in text
    assert "this feed cannot be judged on history" in text


def test_the_report_counts_what_was_set_aside_as_a_governments_own_computers():
    history = read(
        enumerate([legistar("Renewal of data center co-location services for the county")], 1),
        RULES,
        KNOWN,
        {},
    )
    assert history.records == []
    result = run(
        harness_projects(KNOWN, history), [], load_scoring(), history_starts=dt.date(2023, 1, 1)
    )
    text = write(result, history, KNOWN, sweep(result, [3.0]), control_names=["Lamb"])
    assert "because the item is about a government's own computers: 1." in text


def test_the_report_never_carries_the_words_of_an_agenda():
    assert "Orion" not in report() and "Tax abatement" not in report()


# --- what was read near a project ----------------------------------------------------------------


def meeting(government: str, day: str, county: str = MILAM) -> Meeting:
    return Meeting("tx_agendas_own_sites", government, (county,), dt.date.fromisoformat(day))


def test_coverage_counts_only_agendas_from_the_year_before_the_public_date():
    held = [
        meeting("Milam County", "2025-05-30"),  # more than a year before June 1, 2026
        meeting("Milam County", "2026-06-01"),  # the public date itself
        meeting("Hill County", "2026-03-01", county="48217"),
    ]
    assert coverage(RIVER, MILAM, held).kind == "none"
    held.append(meeting("Milam County", "2026-03-01"))
    assert coverage(RIVER, MILAM, held).kind == "the county's only"


def test_coverage_knows_the_projects_own_city_from_its_place():
    cameron = [meeting("Cameron city", "2026-03-01")]
    assert coverage(RIVER, MILAM, cameron).kind == "the city's"  # the row says near Cameron
    assert coverage(QUIET, MILAM, cameron).kind == "another government's only"
    both = [*cameron, meeting("Milam County", "2026-02-01")]
    assert coverage(RIVER, MILAM, both).kind == "the county's and the city's"


def test_a_county_named_in_a_projects_place_is_not_taken_for_a_city_of_that_name():
    rural = known("milam-example-rural", "Milam", place="northwest Cameron County line")
    assert coverage(rural, MILAM, [meeting("Cameron city", "2026-03-01")]).kind == (
        "another government's only"
    )


def test_a_project_with_no_public_date_has_no_coverage_to_speak_of():
    assert coverage(UNDATED, MILAM, [meeting("Milam County", "2026-03-01")]).kind == "none"
