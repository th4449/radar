"""Score one site from its signals. See BUILD_PLAN.md section 8 and config/scoring.yaml.

The rules.

- **Each signal type counts once.** Sixteen soil borings filed on one day are one fact about a
  site, not sixteen. The strongest signal of a type is the one that counts.
- **A signal is worth its type's points, times how sure it is, times its decay.** The points
  halve every half life, counted from the signal's own date.
- **The bonus.** A site earns it once, when signals of enough different types, from different
  sources, are dated within the window of each other. Two types read from one source are not
  independent.
- **Nothing here is a finding.** A score orders the reviewers' queue. Every number in the
  scoring file is a placeholder until the backtest.

The breakdown says where every point came from, so a reviewer can check it against the record.
Nothing in this module touches the database.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from pipeline.config import ScoringFile


@dataclass(frozen=True)
class Scored:
    """A signal, as scoring sees it."""

    signal_type: str
    event_date: dt.date
    confidence: float | None  # None for a signal entered by hand without one: counts in full
    source_id: str
    signal_id: int | None = None


@dataclass(frozen=True)
class Contribution:
    signal_type: str
    signal_id: int | None
    event_date: dt.date
    points: float
    confidence: float
    age_days: int
    decay: float
    value: float


@dataclass(frozen=True)
class SiteScore:
    score: float
    contributions: tuple[Contribution, ...]  # one per signal type, the strongest of each
    bonus: float
    bonus_types: tuple[str, ...]  # the types that earned it
    as_of: dt.date
    signals_total: int
    placeholder: bool

    def detail(self) -> dict:
        """The breakdown stored with the site."""
        return {
            "as_of": self.as_of.isoformat(),
            "score": self.score,
            "placeholder": self.placeholder,
            "signals_total": self.signals_total,
            "signals_counted": len(self.contributions),
            "contributions": [
                {
                    "signal_type": c.signal_type,
                    "signal_id": c.signal_id,
                    "event_date": c.event_date.isoformat(),
                    "points": c.points,
                    "confidence": c.confidence,
                    "age_days": c.age_days,
                    "decay": round(c.decay, 4),
                    "value": round(c.value, 2),
                }
                for c in self.contributions
            ],
            "bonus": {"points": self.bonus, "types": list(self.bonus_types)},
        }


def _contribution(signal: Scored, as_of: dt.date, scoring: ScoringFile) -> Contribution:
    if signal.signal_type not in scoring.signal_types:
        raise ValueError(f"{signal.signal_type} is not a signal type in config/scoring.yaml")
    kind = scoring.signal_types[signal.signal_type]
    age = max(0, (as_of - signal.event_date).days)  # a future date is treated as today
    decay = 0.5 ** (age / kind.half_life_days)
    confidence = 1.0 if signal.confidence is None else float(signal.confidence)
    return Contribution(
        signal.signal_type, signal.signal_id, signal.event_date, float(kind.points), confidence,
        age, decay, kind.points * confidence * decay,
    )  # fmt: skip


def _bonus_types(signals: list[Scored], scoring: ScoringFile) -> tuple[str, ...]:
    """The types that sit within the window of each other, if there are enough of them."""
    rule = scoring.multi_signal_bonus
    ordered = sorted(signals, key=lambda s: s.event_date)
    earned: set[str] = set()
    for first in ordered:
        last_day = first.event_date + dt.timedelta(days=rule.window_days)
        window = [s for s in ordered if first.event_date <= s.event_date <= last_day]
        types = {s.signal_type for s in window}
        sources = {s.source_id for s in window}
        if len(types) >= rule.min_signal_types and len(sources) >= rule.min_signal_types:
            earned |= types
    return tuple(sorted(earned))


def score_site(signals: list[Scored], as_of: dt.date, scoring: ScoringFile) -> SiteScore:
    best: dict[str, Contribution] = {}
    # Ties go to the newer signal, then the lower id, so the same signals always give the
    # same breakdown.
    ordered = sorted(signals, key=lambda s: (s.event_date, -(s.signal_id or 0)), reverse=True)
    for signal in ordered:
        made = _contribution(signal, as_of, scoring)
        held = best.get(signal.signal_type)
        if held is None or made.value > held.value:
            best[signal.signal_type] = made
    contributions = tuple(best[name] for name in sorted(best))
    bonus_types = _bonus_types(signals, scoring)
    bonus = float(scoring.multi_signal_bonus.points) if bonus_types else 0.0
    total = sum(c.value for c in contributions) + bonus
    return SiteScore(
        score=round(total, 2),
        contributions=contributions,
        bonus=bonus,
        bonus_types=bonus_types,
        as_of=as_of,
        signals_total=len(signals),
        placeholder=scoring.placeholder,
    )
