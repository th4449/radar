"""The backtest harness, with made-up projects and signals. Written before the harness.

These tests pin what the words in the report mean: a hit, a miss, a lead time, a false alarm.
No real project is named here.
"""

from __future__ import annotations

import datetime as dt

import pytest

from backtest.harness import (
    Project,
    Signal,
    crossed_on,
    false_alarms,
    match,
    run,
    sweep,
)
from pipeline.config import ScoringFile, load_scoring


def scoring(threshold: float = 40) -> ScoringFile:
    return ScoringFile.model_validate(
        {
            "placeholder": True,
            "signal_types": {
                "air_permit": {"weight": "high", "points": 30, "half_life_days": 365},
                "transmission_filing": {"weight": "high", "points": 30, "half_life_days": 365},
                "well_report": {"weight": "medium", "points": 15, "half_life_days": 365},
                "agenda_keyword": {"weight": "low", "points": 5, "half_life_days": 365},
            },
            "confidence": load_scoring().confidence,
            "multi_signal_bonus": {"min_signal_types": 2, "window_days": 365, "points": 20},
            "clustering": {"near_m": 1000, "same_company_m": 5000},
            "thresholds": {"review_threshold": threshold},
        }
    )


RULES = scoring()
HOOD, HILL, CONTROL = "48221", "48217", "48999"
HERE = (-97.80, 32.44)
NEAR = (-97.805, 32.44)  # about 470 m west
MID = (-97.84, 32.44)  # about 3.7 km west
FAR = (-97.90, 32.44)  # about 9 km west
PUBLIC = dt.date(2026, 6, 1)

_ids = iter(range(1, 10_000))


def day(text: str) -> dt.date:
    return dt.date.fromisoformat(text)


def signal(kind: str, on: str, *, county: str = HOOD, seen: str | None = None, **more) -> Signal:
    source = {"air_permit": "tceq", "transmission_filing": "ercot", "well_report": "twdb"}
    return Signal(
        signal_id=next(_ids),
        signal_type=kind,
        source_id=more.pop("source", source.get(kind, "agendas")),
        county_fips=county,
        event_date=day(on),
        available_on=day(seen or on),
        confidence=more.pop("confidence", 1.0),
        **more,
    )


def project(**more) -> Project:
    base = {
        "key": "p1",
        "name": "Made-up campus",
        "county_fips": HOOD,
        "public_date": PUBLIC,
        "entity_ids": frozenset({7}),
        "names": frozenset({"project falcon"}),
        "point": HERE,
    }
    return Project(**{**base, **more})


# --- which signals belong to a project -----------------------------------------------------------


def test_a_signal_matches_a_project_for_the_reasons_a_site_takes_a_signal():
    p = project()
    clustering = RULES.clustering
    assert match(signal("air_permit", "2026-01-05", entity_id=7), p, clustering) == (
        "the same company"
    )
    assert match(
        signal("agenda_keyword", "2026-01-05", names=frozenset({"project falcon"})), p, clustering
    ) == ("the same project name or number")
    assert match(signal("well_report", "2026-01-05", point=NEAR), p, clustering) == (
        "coordinates within 1000 m"
    )


def test_a_signal_whose_record_names_the_project_belongs_to_it():
    # The backtest's own reason. backtest/history.py reads the record's words for the names of
    # known projects, which the everyday pipeline cannot do.
    p = project()
    named = signal("agenda_keyword", "2026-01-05", names_projects=frozenset({"p1"}))
    assert match(named, p, RULES.clustering) == (
        "the record names the project's company or code name"
    )
    other = signal("agenda_keyword", "2026-01-05", names_projects=frozenset({"p2"}))
    assert match(other, p, RULES.clustering) is None
    elsewhere = signal(
        "agenda_keyword", "2026-01-05", county=HILL, names_projects=frozenset({"p1"})
    )
    assert match(elsewhere, p, RULES.clustering) is None


def test_a_signal_in_another_county_or_with_nothing_in_common_matches_nothing():
    p = project()
    clustering = RULES.clustering
    assert (
        match(signal("air_permit", "2026-01-05", entity_id=7, county=HILL), p, clustering) is None
    )
    assert match(signal("air_permit", "2026-01-05", entity_id=8), p, clustering) is None
    assert match(signal("well_report", "2026-01-05", point=FAR), p, clustering) is None
    assert match(signal("agenda_keyword", "2026-01-05"), p, clustering) is None


def test_the_same_company_far_from_the_project_is_another_place():
    p = project()
    assert (
        match(signal("air_permit", "2026-01-05", entity_id=7, point=FAR), p, RULES.clustering)
        is None
    )
    # With no coordinates on one side, the company's name is all there is to go on.
    assert match(
        signal("air_permit", "2026-01-05", entity_id=7, point=FAR),
        project(point=None),
        RULES.clustering,
    )


# --- when a site would have reached the reviewers ------------------------------------------------


def test_a_site_crosses_the_threshold_on_the_day_the_signal_that_does_it_could_be_seen():
    signals = [
        signal("air_permit", "2026-01-05", seen="2026-01-12"),
        signal("transmission_filing", "2026-02-10", seen="2026-02-20"),
    ]
    # One high signal is 30 points. Two types from two sources add the bonus: over 40.
    assert crossed_on(signals[:1], RULES, 40) is None
    assert crossed_on(signals, RULES, 40) == day("2026-02-20")
    assert crossed_on(signals, RULES, 25) == day("2026-01-12")


def test_a_signal_counts_from_the_day_it_could_be_seen_not_the_day_it_is_dated():
    # A well is drilled in January. Its report is filed in April.
    late = [
        signal("air_permit", "2026-01-05"),
        signal("well_report", "2026-01-20", seen="2026-04-02"),
    ]
    assert crossed_on(late, RULES, 40) == day("2026-04-02")


def test_old_signals_have_decayed_by_the_time_a_new_one_arrives():
    signals = [
        signal("air_permit", "2022-01-05"),
        signal("well_report", "2026-01-20"),
    ]
    # Four years on, the permit is worth under 2 points, and the two are too far apart for
    # the bonus.
    assert crossed_on(signals, RULES, 20) == day("2022-01-05")
    assert crossed_on(signals, RULES, 31) is None


# --- one project's outcome ----------------------------------------------------------------------


def outcome(signals, **more):
    (found,) = run([project(**more)], signals, RULES).outcomes
    return found


def test_a_hit_is_a_site_that_crossed_the_threshold_before_the_project_was_public():
    found = outcome(
        [
            signal("air_permit", "2026-01-05", entity_id=7),
            signal("transmission_filing", "2026-02-20", entity_id=7),
            signal("air_permit", "2025-11-01", entity_id=8),  # some other company
        ]
    )
    assert found.verdict == "hit"
    assert len(found.signals) == 2
    assert found.first_signal == day("2026-01-05")
    assert found.first_by_type == {
        "air_permit": day("2026-01-05"),
        "transmission_filing": day("2026-02-20"),
    }
    assert found.crossed_on == day("2026-02-20")
    assert found.first_signal_lead_days == 147  # January 5 to June 1
    assert found.alert_lead_days == 101  # February 20 to June 1
    assert found.peak_before_public == pytest.approx(77.6, abs=0.5)


def test_a_site_that_crossed_on_or_after_the_public_date_is_late():
    found = outcome(
        [
            signal("air_permit", "2026-05-20", entity_id=7),
            signal("transmission_filing", "2026-06-01", entity_id=7),
        ]
    )
    assert found.verdict == "late"
    assert found.crossed_on == PUBLIC
    assert found.alert_lead_days == 0
    assert found.first_signal_lead_days == 12


def test_signals_before_the_public_date_that_never_reach_the_threshold():
    found = outcome([signal("air_permit", "2026-01-05", entity_id=7)])
    assert found.verdict == "below_threshold"
    assert found.crossed_on is None and found.alert_lead_days is None
    assert found.peak_before_public == pytest.approx(30)


def test_a_project_with_no_signal_before_it_was_public_is_a_miss():
    assert outcome([]).verdict == "no_signal"
    after = outcome([signal("well_report", "2026-08-01", entity_id=7)])
    assert after.verdict == "no_signal"
    assert after.first_signal_lead_days == -61  # the first record came two months after
    assert after.peak_before_public == 0


def test_a_project_with_no_public_date_is_set_aside():
    found = outcome([signal("air_permit", "2026-01-05", entity_id=7)], public_date=None)
    assert found.verdict == "undated"
    assert found.first_signal_lead_days is None


def test_a_project_public_before_the_records_begin_cannot_be_judged():
    result = run(
        [project(public_date=day("2021-03-01"))], [], RULES, history_starts=day("2023-06-18")
    )
    assert result.outcomes[0].verdict == "before_history"


def test_a_signal_that_fits_two_projects_is_given_to_neither():
    """Two projects of one company in one county, neither with coordinates."""
    one = project(key="p1", point=None, names=frozenset())
    two = project(key="p2", point=None, names=frozenset())
    shared = signal("air_permit", "2026-01-05", entity_id=7)
    result = run([one, two], [shared], RULES)
    assert [o.verdict for o in result.outcomes] == ["no_signal", "no_signal"]
    assert result.ambiguous == {shared.signal_id: ("p1", "p2")}


def test_a_signal_that_fits_two_projects_goes_to_the_one_it_sits_on():
    one = project(key="p1")
    two = project(key="p2", point=MID)  # the same company, and near enough to be its site too
    close = signal("air_permit", "2026-01-05", entity_id=7, point=NEAR)
    result = run([one, two], [close], RULES)
    assert [len(o.signals) for o in result.outcomes] == [1, 0]
    assert result.ambiguous == {}


# --- the whole run -------------------------------------------------------------------------------


def a_run(threshold: float = 40):
    projects = [
        project(key="hit"),
        project(key="late", entity_ids=frozenset({8}), names=frozenset(), point=None),
        project(key="below", entity_ids=frozenset({9}), names=frozenset(), point=None),
        project(key="none", entity_ids=frozenset({10}), names=frozenset(), point=None),
        project(key="undated", entity_ids=frozenset({11}), names=frozenset(), point=None,
                public_date=None),
    ]  # fmt: skip
    signals = [
        signal("air_permit", "2026-01-05", entity_id=7),
        signal("transmission_filing", "2026-02-20", entity_id=7),
        signal("air_permit", "2026-05-25", entity_id=8),
        signal("transmission_filing", "2026-06-10", entity_id=8),
        signal("well_report", "2026-03-01", entity_id=9),
        # Two sites in a county with no known project. One reaches 40.
        signal("air_permit", "2026-03-01", entity_id=20, county=CONTROL),
        signal("transmission_filing", "2026-03-15", entity_id=20, county=CONTROL),
        signal("well_report", "2026-04-01", entity_id=21, county=CONTROL),
        # In a test county, on no known project.
        signal("air_permit", "2026-04-01", entity_id=30),
    ]
    return run(projects, signals, scoring(threshold), control_fips={CONTROL})


def test_the_summary_counts_each_kind_of_outcome_and_the_rate_leaves_out_the_undated():
    summary = a_run().summary
    assert summary.verdicts == {
        "hit": 1,
        "late": 1,
        "below_threshold": 1,
        "no_signal": 1,
        "undated": 1,
    }
    assert summary.judged == 4
    assert summary.hit_rate == 0.25
    assert summary.median_alert_lead_days == 101
    # First signals: 147 days, 7 days and 92 days before. The project with none has no lead.
    assert summary.median_first_signal_lead_days == 92
    assert summary.false_alarms == 1
    assert summary.control_sites == 2


def test_a_false_alarm_is_a_site_over_the_threshold_in_a_county_with_no_known_project():
    result = a_run()
    (alarm,) = result.false_alarms
    assert alarm.county_fips == CONTROL
    assert alarm.crossed_on == day("2026-03-15")
    assert alarm.signal_ids and len(alarm.signal_ids) == 2
    # Signals in a test county that fit no known project are listed, and are not false alarms:
    # they may be a project nobody has announced.
    assert len(result.unmatched) == 1
    assert result.unmatched[0].county_fips == HOOD


def test_false_alarms_are_counted_with_the_rules_that_make_sites():
    signals = [
        signal("air_permit", "2026-03-01", point=HERE, county=CONTROL),
        signal("transmission_filing", "2026-03-15", point=NEAR, county=CONTROL),
        signal("transmission_filing", "2026-03-15", point=FAR, county=CONTROL),
        signal("agenda_keyword", "2026-03-15", county=CONTROL),  # nothing holds it to a place
    ]
    sites = false_alarms(signals, RULES, 0)
    assert sorted(len(s.signal_ids) for s in sites) == [1, 2]
    assert [len(s.signal_ids) for s in false_alarms(signals, RULES, 40)] == [2]


def test_agenda_records_of_one_meeting_make_one_site_as_they_do_on_the_radar():
    court = "Example County, meeting of March 9, 2026"
    signals = [
        signal("agenda_keyword", "2026-03-09", county=CONTROL, meeting=court, confidence=0.9),
        signal("agenda_keyword", "2026-03-09", county=CONTROL, meeting=court, confidence=0.9),
        signal("agenda_keyword", "2026-03-09", county=CONTROL),  # a code word: on no site
    ]
    (site,) = false_alarms(signals, RULES, 3)
    assert len(site.signal_ids) == 2
    assert site.peak == pytest.approx(4.5)  # one kind of signal counts once
    assert false_alarms(signals, RULES, 5) == []


def test_a_sweep_shows_what_each_threshold_would_have_caught_and_what_it_would_have_cost():
    rows = sweep(a_run(), [20, 40, 90])
    assert [(r.threshold, r.hits, r.judged, r.false_alarms) for r in rows] == [
        (20, 2, 4, 1),
        (40, 1, 4, 1),
        (90, 0, 4, 0),
    ]
    # A lower bar is crossed sooner: at 20 the first permit alone does it.
    assert rows[0].median_alert_lead_days == 77  # 147 days and 7 days
    assert rows[1].median_alert_lead_days == 101
    assert rows[2].median_alert_lead_days is None
    assert rows[1].hit_rate == 0.25
    # At 40 one project reaches the bar only after it is public. At 20 it reaches it before.
    assert [r.late for r in rows] == [0, 1, 0]
    # The site in a test county that fits no known project peaks at 30.
    assert [r.other_sites for r in rows] == [1, 0, 0]


def test_an_outcome_keeps_the_highest_score_before_the_public_date_and_on_any_day():
    late = next(o for o in a_run().outcomes if o.verdict == "late")
    assert late.peak_before_public == pytest.approx(30)
    assert late.peak == pytest.approx(79.1, abs=0.1)


def test_each_signal_type_is_counted_by_how_often_it_came_first_and_how_early():
    by_type = a_run().summary.by_type
    assert by_type["air_permit"].projects_before_public == 2
    assert by_type["air_permit"].median_lead_days == 77  # 147 and 7
    assert by_type["air_permit"].came_first == 2
    assert by_type["transmission_filing"].projects_before_public == 1
    assert by_type["well_report"].came_first == 1
    assert "agenda_keyword" not in by_type
