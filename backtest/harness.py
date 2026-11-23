"""The backtest: would the radar have seen known projects before they were public?

BUILD_PLAN.md milestone M9. For each known project, find when each signal first appeared and
compare with the date the project became public.

What the words mean here.

- **A known project** is a data center project with a county, and where it is known a company,
  a project name, coordinates and the date it became public. That date and its source are
  research, done by a person, one project at a time.
- **A signal belongs to a project** for the same reasons a signal joins a site in
  pipeline/cluster.py: the same project name or number, the same company, or coordinates close
  by, always inside one county. A signal that fits two projects goes to the one it sits
  nearest. If that cannot be told, it is given to neither and listed for a person.
- **One more reason is the backtest's own:** the record's words carry the project's company
  or code name. An agenda signal carries no company, because an agenda names people, so the
  everyday radar cannot tie it to a site. The backtest knows the projects' names and looks
  for them. A hit that rests on this reason shows what the record held, not what the radar
  would have flagged. The report counts the two apart.
- **A signal counts from the day it could be seen,** not the day it is dated. A well is
  drilled weeks before its report is filed.
- **A hit** is a project whose signals took its score to the review threshold before its
  public date. The score is the one pipeline/score.py gives, replayed day by day.
- **A miss** is every other judged project: `late` crossed on or after the public date,
  `below_threshold` had signals before it and never crossed, `no_signal` had none before it.
- **Not judged:** `undated` has no public date. `before_history` became public before the
  records the radar holds begin.
- **Lead time** is the days from the crossing to the public date. The lead of the first
  signal is reported beside it, since a threshold can be moved and a first signal cannot.
- **A false alarm** is a site over the threshold in a control county, one with no known
  project. Sites are made with the production rules. Each is a candidate only: nobody has
  shown the county has no project.
- **Unmatched** signals in a test county fit no known project. They are listed and are not
  false alarms. A project nobody has announced would look the same.

Nothing here touches the database or the network, and nothing here is a finding about a
company or a place.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import median

from pipeline.cluster import Item, Point, assign, distance_m
from pipeline.config import Clustering, ScoringFile
from pipeline.score import Scored, score_site

JUDGED = ("hit", "late", "below_threshold", "no_signal")
NOT_JUDGED = ("undated", "before_history")


@dataclass(frozen=True)
class Project:
    """A known project. entity_ids and names are what a signal could share with it."""

    key: str
    name: str
    county_fips: str
    public_date: dt.date | None
    entity_ids: frozenset[int] = frozenset()
    names: frozenset[str] = frozenset()  # project code names and project numbers
    point: Point | None = None


@dataclass(frozen=True)
class Signal:
    """A signal as the backtest sees it: what scoring and clustering see, and when it showed."""

    signal_id: int
    signal_type: str
    source_id: str
    county_fips: str
    event_date: dt.date
    available_on: dt.date  # the first day the record was public
    confidence: float | None = None
    entity_id: int | None = None
    names: frozenset[str] = frozenset()
    point: Point | None = None
    meeting: str | None = None  # for a record of an agenda that says "data center"
    # Keys of the known projects whose company or code name the record's words carry. Set by
    # backtest/history.py. The everyday pipeline has no such thing: see match().
    names_projects: frozenset[str] = frozenset()


def _distance(signal: Signal, project: Project) -> float | None:
    if signal.point is None or project.point is None:
        return None
    return distance_m(signal.point, project.point)


def match(signal: Signal, project: Project, rules: Clustering) -> str | None:
    """Why the signal belongs to the project, or None. The reasons of pipeline/cluster.py."""
    if signal.county_fips != project.county_fips:
        return None
    if signal.names & project.names:
        return "the same project name or number"
    if project.key in signal.names_projects:
        return "the record names the project's company or code name"
    distance = _distance(signal, project)
    same_company = signal.entity_id is not None and signal.entity_id in project.entity_ids
    if same_company and (distance is None or distance <= rules.same_company_m):
        return "the same company"
    if distance is not None and distance <= rules.near_m:
        return f"coordinates within {rules.near_m:g} m"
    return None


def _scored(signals: Iterable[Signal]) -> list[Scored]:
    return [
        Scored(s.signal_type, s.event_date, s.confidence, s.source_id, s.signal_id) for s in signals
    ]


def _replay(signals: Iterable[Signal], scoring: ScoringFile) -> list[tuple[dt.date, float]]:
    """The score on each day a signal arrived. Between arrivals a score only decays."""
    signals = list(signals)
    days = sorted({s.available_on for s in signals})
    return [
        (day, score_site(_scored(s for s in signals if s.available_on <= day), day, scoring).score)
        for day in days
    ]


def crossed_on(
    signals: Iterable[Signal], scoring: ScoringFile, threshold: float | None = None
) -> dt.date | None:
    """The first day the signals together reached the threshold. None if they never did."""
    bar = scoring.thresholds.review_threshold if threshold is None else threshold
    return next((day for day, score in _replay(signals, scoring) if score >= bar), None)


@dataclass(frozen=True)
class Outcome:
    project: Project
    signals: tuple[Signal, ...]
    verdict: str
    first_signal: dt.date | None
    first_by_type: dict[str, dt.date]
    crossed_on: dt.date | None
    peak_before_public: float  # the highest score reached before the public date
    peak: float = 0.0  # the highest score reached on any day

    @property
    def first_signal_lead_days(self) -> int | None:
        """Days from the first signal to the public date. Negative when the signal came after."""
        if self.project.public_date is None or self.first_signal is None:
            return None
        return (self.project.public_date - self.first_signal).days

    @property
    def alert_lead_days(self) -> int | None:
        if self.project.public_date is None or self.crossed_on is None:
            return None
        return (self.project.public_date - self.crossed_on).days


def _outcome(
    project: Project,
    signals: list[Signal],
    scoring: ScoringFile,
    threshold: float,
    history_starts: dt.date | None,
) -> Outcome:
    signals = sorted(signals, key=lambda s: (s.available_on, s.signal_id))
    first_by_type: dict[str, dt.date] = {}
    for s in signals:
        first_by_type.setdefault(s.signal_type, s.available_on)
    first = signals[0].available_on if signals else None
    public = project.public_date
    replay = _replay(signals, scoring)
    crossed = next((day for day, score in replay if score >= threshold), None)
    peak = max((score for day, score in replay if public is None or day < public), default=0.0)
    if public is None:
        verdict = "undated"
    elif history_starts is not None and public <= history_starts:
        verdict = "before_history"
    elif crossed is not None and crossed < public:
        verdict = "hit"
    elif crossed is not None:
        verdict = "late"
    elif first is not None and first < public:
        verdict = "below_threshold"
    else:
        verdict = "no_signal"
    ever = max((score for _, score in replay), default=0.0)
    return Outcome(project, tuple(signals), verdict, first, first_by_type, crossed, peak, ever)


@dataclass(frozen=True)
class SiteReplay:
    """A site made from signals that fit no known project, and when it crossed the threshold."""

    county_fips: str
    signal_ids: tuple[int, ...]
    first_signal: dt.date
    crossed_on: dt.date | None
    peak: float


def _sites(signals: list[Signal], scoring: ScoringFile, threshold: float) -> list[SiteReplay]:
    """The sites the production rules would make of these signals, each replayed."""
    by_id = {s.signal_id: s for s in signals}
    items = [
        Item(s.signal_id, s.county_fips, s.entity_id, s.point, s.names, s.event_date, s.meeting)
        for s in signals
    ]
    out = []
    for group in assign(items, [], scoring.clustering).new_sites:
        members = [by_id[m.signal_id] for m in group.members]
        replay = _replay(members, scoring)
        out.append(
            SiteReplay(
                county_fips=group.county_fips,
                signal_ids=tuple(sorted(m.signal_id for m in members)),
                first_signal=min(m.available_on for m in members),
                crossed_on=next((day for day, score in replay if score >= threshold), None),
                peak=max(score for _, score in replay),
            )
        )
    return out


def false_alarms(
    signals: Iterable[Signal], scoring: ScoringFile, threshold: float | None = None
) -> list[SiteReplay]:
    """The sites these signals make that reached the threshold. For control counties."""
    bar = scoring.thresholds.review_threshold if threshold is None else threshold
    return [s for s in _sites(list(signals), scoring, bar) if s.crossed_on is not None]


@dataclass(frozen=True)
class TypeCount:
    projects_before_public: int  # judged projects with a signal of this type before the date
    median_lead_days: float | None  # of the first such signal
    came_first: int  # judged projects whose first signal of all was of this type


@dataclass(frozen=True)
class Summary:
    threshold: float
    verdicts: dict[str, int]
    judged: int
    hits: int
    hit_rate: float | None
    median_alert_lead_days: float | None  # over hits
    median_first_signal_lead_days: float | None  # over judged projects with any signal
    control_sites: int
    false_alarms: int
    by_type: dict[str, TypeCount]


@dataclass(frozen=True)
class Result:
    scoring: ScoringFile
    threshold: float
    history_starts: dt.date | None
    outcomes: tuple[Outcome, ...]
    ambiguous: dict[int, tuple[str, ...]]  # a signal -> the projects it fits equally
    unmatched: tuple[SiteReplay, ...]  # in test counties, on no known project
    control: tuple[SiteReplay, ...]  # every site in the control counties
    false_alarms: tuple[SiteReplay, ...]
    summary: Summary
    # Kept so another threshold can be tried without matching again.
    control_signals: tuple[Signal, ...] = ()


def _median(values: list[int]) -> float | None:
    return median(values) if values else None


def _by_type(outcomes: Iterable[Outcome]) -> dict[str, TypeCount]:
    leads: dict[str, list[int]] = {}
    first: Counter[str] = Counter()
    for o in outcomes:
        if o.verdict not in JUDGED:
            continue
        public = o.project.public_date
        for kind, day in o.first_by_type.items():
            if day < public:
                leads.setdefault(kind, []).append((public - day).days)
        if o.signals:
            first[o.signals[0].signal_type] += 1
    return {
        kind: TypeCount(len(leads.get(kind, [])), _median(leads.get(kind, [])), first[kind])
        for kind in sorted(set(leads) | set(first))
    }


def _summary(
    outcomes: tuple[Outcome, ...],
    control: tuple[SiteReplay, ...],
    alarms: tuple[SiteReplay, ...],
    threshold: float,
) -> Summary:
    verdicts = dict(Counter(o.verdict for o in outcomes))
    judged = [o for o in outcomes if o.verdict in JUDGED]
    hits = [o for o in judged if o.verdict == "hit"]
    first_leads = [o.first_signal_lead_days for o in judged if o.first_signal is not None]
    return Summary(
        threshold=threshold,
        verdicts=verdicts,
        judged=len(judged),
        hits=len(hits),
        hit_rate=len(hits) / len(judged) if judged else None,
        median_alert_lead_days=_median([o.alert_lead_days for o in hits]),
        median_first_signal_lead_days=_median(first_leads),
        control_sites=len(control),
        false_alarms=len(alarms),
        by_type=_by_type(outcomes),
    )


def _assigned(
    projects: list[Project], signals: list[Signal], rules: Clustering
) -> tuple[dict[str, list[Signal]], dict[int, tuple[str, ...]], list[Signal]]:
    """Each project's signals, the signals that fit several equally, and those that fit none."""
    mine: dict[str, list[Signal]] = {p.key: [] for p in projects}
    ambiguous: dict[int, tuple[str, ...]] = {}
    unmatched: list[Signal] = []
    for s in signals:
        fits = [p for p in projects if match(s, p, rules)]
        if len(fits) > 1:
            # The project it sits nearest, when one is nearer than every other.
            placed = sorted((d, p.key) for p in fits if (d := _distance(s, p)) is not None)
            alone = len(placed) == len(fits) and placed[0][0] < placed[1][0]
            if not alone:
                ambiguous[s.signal_id] = tuple(sorted(p.key for p in fits))
                continue
            fits = [p for p in fits if p.key == placed[0][1]]
        if fits:
            mine[fits[0].key].append(s)
        else:
            unmatched.append(s)
    return mine, ambiguous, unmatched


def run(
    projects: Iterable[Project],
    signals: Iterable[Signal],
    scoring: ScoringFile,
    *,
    control_fips: Iterable[str] = (),
    history_starts: dt.date | None = None,
    threshold: float | None = None,
) -> Result:
    """Judge every project and count the false alarms, at one threshold."""
    projects = list(projects)
    keys = [p.key for p in projects]
    if len(set(keys)) != len(keys):
        raise ValueError("two projects share a key")
    control_fips = set(control_fips)
    in_control = [p.key for p in projects if p.county_fips in control_fips]
    if in_control:
        raise ValueError(f"a control county holds a known project: {in_control}")
    bar = scoring.thresholds.review_threshold if threshold is None else threshold
    signals = list(signals)
    control_signals = [s for s in signals if s.county_fips in control_fips]
    test_signals = [s for s in signals if s.county_fips not in control_fips]
    mine, ambiguous, loose = _assigned(projects, test_signals, scoring.clustering)
    outcomes = tuple(_outcome(p, mine[p.key], scoring, bar, history_starts) for p in projects)
    control = tuple(_sites(control_signals, scoring, bar))
    alarms = tuple(s for s in control if s.crossed_on is not None)
    return Result(
        scoring=scoring,
        threshold=bar,
        history_starts=history_starts,
        outcomes=outcomes,
        ambiguous=ambiguous,
        unmatched=tuple(_sites(loose, scoring, bar)),
        control=control,
        false_alarms=alarms,
        summary=_summary(outcomes, control, alarms, bar),
        control_signals=tuple(control_signals),
    )


@dataclass(frozen=True)
class SweepRow:
    threshold: float
    judged: int
    hits: int
    hit_rate: float | None
    median_alert_lead_days: float | None
    false_alarms: int
    late: int = 0  # judged projects that reached the bar only on or after the public date
    other_sites: int = 0  # sites in test counties that fit no known project and reached it


def sweep(result: Result, thresholds: Iterable[float]) -> list[SweepRow]:
    """What each threshold would have caught, and how many control sites it would have flagged.

    The signals stay where the run put them. Only the bar moves.
    """
    rows = []
    for bar in thresholds:
        outcomes = tuple(
            _outcome(o.project, list(o.signals), result.scoring, bar, result.history_starts)
            for o in result.outcomes
        )
        control = tuple(_sites(list(result.control_signals), result.scoring, bar))
        alarms = tuple(s for s in control if s.crossed_on is not None)
        made = _summary(outcomes, control, alarms, bar)
        rows.append(
            SweepRow(
                bar, made.judged, made.hits, made.hit_rate, made.median_alert_lead_days,
                made.false_alarms, made.verdicts.get("late", 0),
                sum(1 for site in result.unmatched if site.peak >= bar),
            )
        )  # fmt: skip
    return rows
