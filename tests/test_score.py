"""Scoring, with synthetic signals. Written before the scoring code.

Every number comes from config/scoring.yaml, which holds placeholders until the backtest.
These tests pin the rules, not the numbers: they build their own scoring file where a number
matters.
"""

from __future__ import annotations

import datetime as dt

import pytest

from pipeline.config import ScoringFile, load_scoring
from pipeline.score import Scored, score_site

TODAY = dt.date(2026, 11, 20)


def scoring(**overrides) -> ScoringFile:
    data = {
        "placeholder": True,
        "signal_types": {
            "air_permit": {"weight": "high", "points": 30, "half_life_days": 365},
            "transmission_filing": {"weight": "high", "points": 30, "half_life_days": 365},
            "well_report": {"weight": "medium", "points": 15, "half_life_days": 365},
            "agenda_keyword": {"weight": "low", "points": 5, "half_life_days": 100},
        },
        "confidence": load_scoring().confidence,
        "multi_signal_bonus": {"min_signal_types": 2, "window_days": 365, "points": 20},
        "clustering": {"near_m": 1000, "same_company_m": 5000},
        "thresholds": {"review_threshold": 40},
    }
    data.update(overrides)
    return ScoringFile.model_validate(data)


RULES = scoring()


def sig(
    signal_type: str = "air_permit",
    days_ago: int = 0,
    confidence: float | None = 1.0,
    source: str | None = None,
    signal_id: int | None = None,
) -> Scored:
    return Scored(
        signal_type=signal_type,
        event_date=TODAY - dt.timedelta(days=days_ago),
        confidence=confidence,
        source_id=source or f"source_of_{signal_type}",
        signal_id=signal_id,
    )


def score(*signals: Scored, rules: ScoringFile = RULES) -> float:
    return score_site(list(signals), TODAY, rules).score


# --- one signal ---------------------------------------------------------------------------------


def test_a_site_with_no_signals_scores_nothing():
    out = score_site([], TODAY, RULES)
    assert out.score == 0 and out.contributions == () and out.bonus == 0


def test_a_fresh_signal_scores_its_points():
    assert score(sig("air_permit")) == 30
    assert score(sig("well_report")) == 15


def test_points_halve_every_half_life():
    assert score(sig("air_permit", days_ago=365)) == 15
    assert score(sig("air_permit", days_ago=730)) == 7.5
    assert score(sig("agenda_keyword", days_ago=100)) == 2.5


def test_decay_is_smooth_between_half_lives():
    half_way = score(sig("air_permit", days_ago=182))
    assert 15 < half_way < 30
    assert half_way == pytest.approx(30 * 0.5 ** (182 / 365), abs=0.01)


def test_each_type_decays_at_its_own_rate():
    fast = score(sig("agenda_keyword", days_ago=200))  # two half lives of 100 days
    slow = score(sig("well_report", days_ago=200))
    assert fast == 1.25
    assert slow == pytest.approx(15 * 0.5 ** (200 / 365), abs=0.01)


def test_a_signal_dated_in_the_future_scores_no_more_than_a_fresh_one():
    assert score(sig("air_permit", days_ago=-30)) == 30


def test_confidence_scales_the_points():
    assert score(sig("air_permit", confidence=0.9)) == 27
    assert score(sig("air_permit", confidence=0.3)) == 9
    assert score(sig("air_permit", confidence=0.5, days_ago=365)) == 7.5


def test_a_signal_entered_without_a_confidence_counts_in_full():
    assert score(sig("air_permit", confidence=None)) == 30


def test_an_unknown_signal_type_is_an_error_not_a_zero():
    with pytest.raises(ValueError, match="made_up"):
        score(sig("made_up"))


# --- several signals of one type ----------------------------------------------------------------


def test_many_signals_of_one_type_count_once():
    # Sixteen soil borings filed on one day are one fact about a site, not sixteen.
    borings = [sig("well_report", confidence=0.5, signal_id=i) for i in range(16)]
    assert score(*borings) == 7.5


def test_the_strongest_signal_of_a_type_is_the_one_that_counts():
    out = score_site(
        [
            sig("well_report", days_ago=400, confidence=0.9, signal_id=1),
            sig("well_report", days_ago=10, confidence=0.5, signal_id=2),
            sig("well_report", days_ago=10, confidence=0.3, signal_id=3),
        ],
        TODAY,
        RULES,
    )
    (only,) = out.contributions
    assert only.signal_id == 2
    assert out.score == pytest.approx(15 * 0.5 * 0.5 ** (10 / 365), abs=0.01)


# --- the multi-signal bonus ---------------------------------------------------------------------


def test_two_types_within_the_window_earn_the_bonus():
    out = score_site([sig("air_permit"), sig("well_report", days_ago=200)], TODAY, RULES)
    assert out.bonus == 20
    assert out.bonus_types == ("air_permit", "well_report")
    assert out.score == pytest.approx(30 + 15 * 0.5 ** (200 / 365) + 20, abs=0.01)


def test_two_types_further_apart_than_the_window_earn_nothing():
    out = score_site([sig("air_permit"), sig("well_report", days_ago=366)], TODAY, RULES)
    assert out.bonus == 0 and out.bonus_types == ()


def test_the_window_is_between_the_signals_not_back_from_today():
    # Both are old, and close to each other.
    out = score_site(
        [sig("air_permit", days_ago=900), sig("well_report", days_ago=800)], TODAY, RULES
    )
    assert out.bonus == 20


def test_exactly_the_window_apart_still_counts():
    assert score_site([sig("air_permit"), sig("well_report", days_ago=365)], TODAY, RULES).bonus


def test_one_type_however_many_signals_earns_no_bonus():
    out = score_site([sig("air_permit", signal_id=i) for i in range(5)], TODAY, RULES)
    assert out.bonus == 0


def test_two_types_from_one_source_are_not_independent():
    same = [sig("air_permit", source="tx_one_feed"), sig("well_report", source="tx_one_feed")]
    assert score_site(same, TODAY, RULES).bonus == 0
    other = [sig("air_permit", source="tx_one_feed"), sig("well_report", source="tx_other")]
    assert score_site(other, TODAY, RULES).bonus == 20


def test_the_bonus_is_paid_once_however_many_types():
    out = score_site(
        [sig("air_permit"), sig("well_report"), sig("transmission_filing")], TODAY, RULES
    )
    assert out.bonus == 20
    assert out.score == 30 + 15 + 30 + 20


def test_a_bonus_that_needs_three_types():
    three = scoring(multi_signal_bonus={"min_signal_types": 3, "window_days": 365, "points": 20})
    two = [sig("air_permit"), sig("well_report")]
    assert score_site(two, TODAY, three).bonus == 0
    assert score_site([*two, sig("transmission_filing")], TODAY, three).bonus == 20
    # The third type is too far from the first two.
    spread = [*two, sig("transmission_filing", days_ago=500)]
    assert score_site(spread, TODAY, three).bonus == 0


def test_weak_signals_can_earn_the_bonus_and_still_stay_under_the_threshold():
    out = score_site(
        [sig("air_permit", confidence=0.3), sig("well_report", confidence=0.3)], TODAY, RULES
    )
    assert out.bonus == 20
    assert out.score == 9 + 4.5 + 20
    assert out.score < RULES.thresholds.review_threshold


# --- what a reviewer sees -----------------------------------------------------------------------


def test_the_breakdown_says_where_every_point_came_from():
    out = score_site(
        [
            sig("air_permit", days_ago=365, confidence=0.9, signal_id=11),
            sig("well_report", days_ago=30, confidence=0.5, signal_id=12),
            sig("well_report", days_ago=30, confidence=0.3, signal_id=13),
        ],
        TODAY,
        RULES,
    )
    detail = out.detail()
    assert detail["as_of"] == "2026-11-20" and detail["placeholder"] is True
    assert detail["signals_counted"] == 2 and detail["signals_total"] == 3
    air = next(c for c in detail["contributions"] if c["signal_type"] == "air_permit")
    assert air == {
        "signal_type": "air_permit", "signal_id": 11, "event_date": "2025-11-20",
        "points": 30.0, "confidence": 0.9, "age_days": 365, "decay": 0.5, "value": 13.5,
    }  # fmt: skip
    assert detail["bonus"] == {"points": 20.0, "types": ["air_permit", "well_report"]}
    total = sum(c["value"] for c in detail["contributions"]) + detail["bonus"]["points"]
    assert detail["score"] == out.score == pytest.approx(total, abs=0.01)


def test_the_same_signals_in_any_order_give_the_same_score():
    signals = [
        sig("air_permit", days_ago=40, signal_id=1),
        sig("well_report", days_ago=3, signal_id=2),
        sig("well_report", days_ago=3, signal_id=3),
        sig("transmission_filing", days_ago=700, signal_id=4),
    ]
    forward = score_site(signals, TODAY, RULES)
    backward = score_site(signals[::-1], TODAY, RULES)
    assert forward.detail() == backward.detail()


def test_the_real_scoring_file_works_and_is_still_marked_placeholder():
    real = load_scoring()
    out = score_site([sig("air_permit"), sig("well_report")], TODAY, real)
    assert out.score == 30 + 15 + 20
    assert out.detail()["placeholder"] is True
