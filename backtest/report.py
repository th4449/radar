"""Write the backtest report. BUILD_PLAN.md milestone M9.

The report says what the harness measured and nothing more. Every number in it is counted
here from the harness result and the history that was read.

**A signal that fits no known project is unreviewed.** The public site shows a record only
after reviewers confirm it, and this file is public too. So a company is named here only when
it is already in the list of known projects. A site that fits no known project is described
by its county, its kind and its count, never by a name.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from statistics import median

from backtest.harness import JUDGED, Outcome, Result, SiteReplay, SweepRow, match
from backtest.history import History, Meeting, Record
from backtest.projects import KnownProject
from pipeline.config import load_all_counties

BY_NAME = "the record names the project's company or code name"
YEAR = 365

_PLACE_KIND = re.compile(r"\s+(city|town|village)$")
_A_COUNTY = re.compile(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+County")

VERDICTS = {
    "hit": "reached the review threshold before the public date",
    "late": "reached it on or after the public date",
    "below_threshold": "had a signal before the public date and never reached it",
    "no_signal": "had no signal before the public date",
    "undated": "not judged: no public date was found",
    "before_history": "not judged: public before the records begin",
}
SOURCE_NAMES = {
    "tx_agendas_legistar": "Agendas on Legistar",
    "tx_agendas_own_sites": "Agenda files on governments' own sites",
    "tx_ercot_rpg": "ERCOT planning group files",
    "tx_twdb_well_reports": "State well reports",
    "tx_tceq_air_pending_legacy": "TCEQ pending air permits",
}
TYPE_NAMES = {
    "agenda_keyword": "agenda item or file",
    "transmission_filing": "ERCOT planning file",
    "well_report": "well report",
    "air_permit": "pending air permit",
}
RULE_NAMES = {
    "direct_term": 'says "data center"',
    "listed_company": "company on the Comptroller's list",
    "listed_company_loose": "company named like one on the list",
    "project_code_name": '"Project" and a code name',
    "code_word": "a code word",
}


# --- what was read near a project ---------------------------------------------------------------


@dataclass(frozen=True)
class Coverage:
    """The agendas the radar held from a project's county in the year before it was public."""

    county_government: bool
    own_city: bool
    governments: tuple[str, ...]

    @property
    def kind(self) -> str:
        if self.county_government and self.own_city:
            return "the county's and the city's"
        if self.own_city:
            return "the city's"
        if self.county_government:
            return "the county's only"
        if self.governments:
            return "another government's only"
        return "none"


COVERAGE_ORDER = (
    "the county's and the city's",
    "the city's",
    "the county's only",
    "another government's only",
    "none",
)


def coverage(
    known: KnownProject, county_fips: str, meetings: Iterable[Meeting], days: int = YEAR
) -> Coverage:
    """Which governments' agendas were read for the year before the project was public."""
    public = known.public_date
    if public is None:
        return Coverage(False, False, ())
    first = public - dt.timedelta(days=days)
    governments = sorted(
        {m.government for m in meetings if county_fips in m.counties and first <= m.day < public}
    )
    county = any(g.endswith(" County") for g in governments)
    place = _A_COUNTY.sub(" ", known.place)  # "northwest Harris County" names no city
    city = any(
        re.search(rf"(?<![A-Za-z]){re.escape(_PLACE_KIND.sub('', g))}(?![A-Za-z])", place)
        for g in governments
        if not g.endswith(" County")
    )
    return Coverage(county, city, tuple(governments))


# --- small helpers ------------------------------------------------------------------------------


def _date(day: dt.date | None) -> str:
    return f"{day:%b} {day.day}, {day.year}" if day else "none"


def _number(value: float | None) -> str:
    if value is None:
        return "none"
    return f"{value:g}"


def _table(head: Sequence[str], rows: Iterable[Sequence[object]]) -> list[str]:
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return out


def _own_way(outcome: Outcome, result: Result) -> list:
    """The project's signals the everyday radar could have tied to it: not by name."""
    plain = [dataclasses.replace(s, names_projects=frozenset()) for s in outcome.signals]
    return [s for s in plain if match(s, outcome.project, result.scoring.clustering)]


def _held(site: SiteReplay, by_id: dict[int, Record]) -> str:
    """What holds a site that fits no known project together. Never a name."""
    members = [by_id[i].signal for i in site.signal_ids]
    if any(s.entity_id is not None or s.point is not None for s in members):
        return "a company or coordinates"
    if any(n.startswith("Project ") for s in members for n in s.names):
        return 'a "Project" code name'
    return "a project number"


def _loose_direct(history: History, result: Result, tied: dict[int, str]) -> list[Record]:
    """Records tied to no project that say "data center", or are a planning file that names
    the county, seen in the year before a judged project in the same county became public."""
    public: dict[str, list[dt.date]] = {}
    for o in result.outcomes:
        if o.verdict in JUDGED:
            public.setdefault(o.project.county_fips, []).append(o.project.public_date)
    out = []
    for r in history.records:
        s = r.signal
        wanted = r.rule == "direct_term" or s.signal_type == "transmission_filing"
        if not wanted or s.signal_id in tied or s.signal_id in result.ambiguous:
            continue
        if any(0 < (day - s.available_on).days <= YEAR for day in public.get(s.county_fips, [])):
            out.append(r)
    return sorted(out, key=lambda r: (r.signal.county_fips, r.signal.available_on, r.reference))


# --- the report ---------------------------------------------------------------------------------


def write(
    result: Result,
    history: History,
    known: Sequence[KnownProject],
    sweep_rows: Sequence[SweepRow],
    *,
    control_names: Sequence[str],
) -> str:
    by_id = {r.signal.signal_id: r for r in history.records}
    by_key = {k.key: k for k in known}
    counties = {c.fips: c.name for c in load_all_counties("TX").counties}
    summary = result.summary
    outcomes = list(result.outcomes)
    judged = [o for o in outcomes if o.verdict in JUDGED]
    early = [o for o in judged if o.first_signal and o.first_signal < o.project.public_date]
    after = [o for o in judged if o.signals and o not in early]
    own_way_early = [
        o for o in early if any(s.available_on < o.project.public_date for s in _own_way(o, result))
    ]
    unplaced = sum(1 for r in history.records if not r.signal.county_fips)
    control_fips = {f for f, n in counties.items() if n in set(control_names)}
    control_signals = [r for r in history.records if r.signal.county_fips in control_fips]
    tied = {s.signal_id: o.project.key for o in outcomes for s in o.signals}

    lines: list[str] = []
    add = lines.append

    add("# Texas backtest")
    add("")
    add(
        "BUILD_PLAN.md milestone M9. Written by `python -m backtest.run` from the history "
        f"the radar held on {_date(history.read_through)}. Do not edit by hand."
    )
    add("")
    add(
        "**Nothing here is a finding about a company or a place.** A signal is a dated public "
        "record that uses a term the radar looks for. The scores and the threshold are "
        "placeholders."
    )
    add("")
    add("## In short")
    add("")
    add(
        f"- **{summary.hits} of {summary.judged} judged projects reached the review threshold "
        f"of {_number(result.threshold)} before they were public.**"
    )
    add(
        f"- **{len(early)} of {summary.judged} had any signal before the public date.** "
        f"{len(own_way_early)} of those could have been tied to the project by the everyday "
        "radar. The rest were tied here by the project's name in the record's words, which "
        "only the backtest can do."
    )
    add(f"- {len(after)} more had a signal only on or after the public date.")
    top = max(outcomes, key=lambda o: o.peak, default=None)
    add(
        f"- **The highest score any known project reached on any day is "
        f"{_number(top.peak if top else 0.0)}.** At {_number(result.threshold)}, the radar "
        "would have sent none of them to a reviewer, before or after it was public."
        if top is None or top.peak < result.threshold
        else f"- The highest score any known project reached on any day is {_number(top.peak)}."
    )
    lead = [o.alert_lead_days for o in judged if o.verdict == "hit"]
    add(
        f"- Median lead time over hits: {_number(median(lead) if lead else None)}"
        + (" days." if lead else ". There is no hit to measure.")
    )
    add(
        f"- False alarms in the {len(control_names)} control counties: {summary.false_alarms}. "
        f"The history holds {len(control_signals)} signals there."
    )
    add("")

    add("## What was judged")
    add("")
    add(
        f"`known_projects_tx.csv` holds {len(known)} projects. A project is judged when it has "
        f"a public date after {_date(result.history_starts)}, the day the history starts."
    )
    add("")
    counts = Counter(o.verdict for o in outcomes)
    add_all = lines.extend
    add_all(
        _table(
            ("Verdict", "Projects", "Meaning"),
            [(v, counts.get(v, 0), VERDICTS[v]) for v in VERDICTS],
        )
    )
    add("")

    add("## What the radar held")
    add("")
    rows = []
    for source, name in SOURCE_NAMES.items():
        c = history.counts.get(source, {})
        rows.append(
            (name, c.get("documents", 0), c.get("records", 0), c.get("signals", 0),
             c.get("held_back", 0))
        )  # fmt: skip
    add_all(_table(("Source", "Documents", "Records read", "Signals", "Held back"), rows))
    add("")
    governments = {m.government for m in history.meetings}
    add(
        f"- {len(history.meetings)} dated agendas from {len(governments)} governments were "
        "read. A record is an agenda item, an agenda file, a well report, a planning file or "
        "a row of a permit list."
    )
    add(
        f"- {len(history.records)} signals in all. {unplaced} carry no county and can sit on "
        "no site: the planning files that name no test county and every pending air permit."
    )
    add(
        "- A record is held back when its named party may be a person. It makes no signal and "
        "is counted by its number."
    )
    if history.listed_later:
        add(
            f"- {history.listed_later} records gave no signal because the company was "
            "registered on the Comptroller's list only after the record's date."
        )
    if history.errors:
        add(f"- **{len(history.errors)} documents could not be read.**")
    add("")

    add("## Projects that had a signal")
    add("")
    rows = []
    for o in sorted(outcomes, key=lambda o: (o.first_signal or dt.date.max, o.project.key)):
        if not o.signals:
            continue
        reasons = sorted({match(s, o.project, result.scoring.clustering) or "" for s in o.signals})
        kinds = Counter(TYPE_NAMES[s.signal_type] for s in o.signals)
        days = o.first_signal_lead_days
        rows.append(
            (
                f"`{o.project.key}`",
                counties[o.project.county_fips],
                _date(o.project.public_date),
                _date(o.first_signal),
                "not judged" if days is None else f"{days:+d}",
                ", ".join(f"{n} {k}" for k, n in sorted(kinds.items())),
                _number(o.peak_before_public),
                o.verdict,
                "; ".join(reasons),
            )
        )
    add_all(
        _table(
            ("Project", "County", "Public", "First signal seen", "Days ahead", "Signals",
             "Peak score before public", "Verdict", "Tied by"),
            rows,
        )
    )  # fmt: skip
    add("")
    add(
        "Days ahead is the public date less the day the first signal could be seen. A minus "
        "sign means the signal came after the project was public."
    )
    add("")

    add("## What was read near the projects that were judged")
    add("")
    add(
        "For each judged project: the agendas the radar held from its county, dated in the "
        "year before its public date. The city is one the project's row names in its place, "
        "which for a site outside any city is the nearest one."
    )
    add("")
    cover = {o.project.key: coverage(by_key[o.project.key], o.project.county_fips,
                                     history.meetings) for o in judged}  # fmt: skip
    kinds = Counter(c.kind for c in cover.values())
    with_signal = Counter(cover[o.project.key].kind for o in early)
    add_all(
        _table(
            ("Agendas held", "Judged projects", "With a signal before public"),
            [(k, kinds.get(k, 0), with_signal.get(k, 0)) for k in COVERAGE_ORDER],
        )
    )
    add("")
    add(
        "The well reports and the ERCOT planning files cover every county from "
        f"{_date(result.history_starts)}. The pending air permit lists show only what is "
        "pending today."
    )
    add("")
    rows = []
    for fips in sorted({o.project.county_fips for o in judged}, key=lambda f: counties[f]):
        here = [o for o in judged if o.project.county_fips == fips]
        meetings = [m for m in history.meetings if fips in m.counties]
        rows.append(
            (
                counties[fips],
                len(here),
                sum(1 for o in here if o in early),
                len({m.government for m in meetings}),
                len(meetings),
                _date(min((m.day for m in meetings), default=None)),
            )
        )
    add_all(
        _table(
            ("County", "Judged projects", "With a signal before public", "Governments read",
             "Agendas held", "Oldest agenda held"),
            rows,
        )
    )  # fmt: skip
    add("")

    add("## By kind of signal")
    add("")
    rows = []
    for kind, name in TYPE_NAMES.items():
        mine = [r for r in history.records if r.signal.signal_type == kind]
        seen = summary.by_type.get(kind)
        rows.append(
            (
                name,
                len(mine),
                sum(1 for r in mine if r.signal.signal_id in tied),
                seen.projects_before_public if seen else 0,
                _number(seen.median_lead_days if seen else None),
            )
        )
    add_all(
        _table(
            ("Kind", "Signals", "Tied to a known project", "Projects with one before public",
             "Median days ahead"),
            rows,
        )
    )  # fmt: skip
    add("")

    add("## By the rule that made the signal")
    add("")
    rows = []
    for rule, name in RULE_NAMES.items():
        mine = [r for r in history.records if r.rule == rule]
        rows.append((name, len(mine), sum(1 for r in mine if r.signal.signal_id in tied)))
    add_all(_table(("Strongest reason", "Signals", "Tied to a known project"), rows))
    add("")
    add(
        "A signal tied to no known project is not shown to be wrong. The list of known "
        "projects is not complete."
    )
    add("")

    add("## Records tied to no project that a person should read")
    add("")
    loose = _loose_direct(history, result, tied)
    add(
        f'{len(loose)} records that say "data center", or are a planning file that names the '
        "county, were seen in the year before a judged project in the same county became "
        "public. The program ties a record to a project only by a name the list of known "
        "projects carries, and a county calls a project by names the list does not have. "
        "**Any of these may be an early record of a known project. None is counted as one.** "
        "Many are a government's own computer rooms."
    )
    add("")
    if loose:
        add_all(
            _table(
                ("County", "Seen", "Kind", "Record"),
                [(counties[r.signal.county_fips], r.signal.available_on.isoformat(),
                  TYPE_NAMES[r.signal.signal_type], r.reference) for r in loose],
            )
        )  # fmt: skip
        add("")

    add("## Pending air permits")
    add("")
    permits = [r for r in history.records if r.signal.signal_type == "air_permit"]
    named, ahead = 0, 0
    for r in permits:
        mine = [o.project for o in outcomes if r.signal.entity_id in o.project.entity_ids]
        named += bool(mine)
        ahead += any(p.public_date and r.signal.event_date < p.public_date for p in mine)
    add(
        f"- The two lists give {len(permits)} signals. They give no county, so none can sit "
        "on a site or be tied to a project by the rules above."
    )
    add(
        f"- By the applicant's name alone, in any county, {named} name a company of a known "
        f"project. **{ahead} of those were received before that project's public date.**"
    )
    add(
        "- The lists show what is pending today. A permit decided before November 2026 is "
        "gone from them, so this feed cannot be judged on history."
    )
    add("")

    add("## Control counties")
    add("")
    add(f"{', '.join(control_names)}.")
    add("")
    add(
        f"- Signals: {len(control_signals)}. Sites: {summary.control_sites}. "
        f"False alarms: {summary.false_alarms}."
    )
    add(
        "- **This is a weak test.** The radar reads no agenda in a control county. Only the "
        "well reports and the ERCOT planning files could have given a signal there."
    )
    add("")

    add("## Sites that fit no known project")
    add("")
    add(
        f"In the test counties, signals that fit no known project make {len(result.unmatched)} "
        "sites under the everyday rules. None is named here: none has been reviewed."
    )
    add("")
    held = Counter(_held(s, by_id) for s in result.unmatched)
    peaks: dict[str, float] = {}
    for s in result.unmatched:
        peaks[_held(s, by_id)] = max(peaks.get(_held(s, by_id), 0.0), s.peak)
    over = Counter(_held(s, by_id) for s in result.unmatched if s.crossed_on is not None)
    add_all(
        _table(
            ("Held together by", "Sites", "Highest score", "At or over the threshold"),
            [(k, n, _number(peaks[k]), over.get(k, 0)) for k, n in held.most_common()],
        )
    )
    add("")
    anchored = [s for s in result.unmatched if _held(s, by_id) == "a company or coordinates"]
    if anchored:
        add("The sites held by a company or coordinates:")
        add("")
        rows = [
            (
                counties.get(s.county_fips, s.county_fips),
                ", ".join(sorted({TYPE_NAMES[by_id[i].signal.signal_type]
                                  for i in s.signal_ids})),
                len(s.signal_ids),
                _date(s.first_signal),
                _number(s.peak),
            )
            for s in sorted(anchored, key=lambda s: s.first_signal)
        ]  # fmt: skip
        add_all(_table(("County", "Kind", "Signals", "First seen", "Highest score"), rows))
        add("")
    add(
        f"{len(result.ambiguous)} signals fit two known projects equally and were given to neither."
    )
    add("")

    add("## Other thresholds")
    add("")
    add("The same signals, with only the bar moved.")
    add("")
    add_all(
        _table(
            ("Threshold", "Hits", "Reached it only after public", "Judged", "Hit rate",
             "Median lead, days", "False alarms in control counties",
             "Sites that fit no known project, at or over"),
            [
                (
                    _number(r.threshold),
                    r.hits,
                    r.late,
                    r.judged,
                    "none" if r.hit_rate is None else f"{r.hit_rate:.0%}",
                    _number(r.median_alert_lead_days),
                    r.false_alarms,
                    r.other_sites,
                )
                for r in sweep_rows
            ],
        )
    )  # fmt: skip
    add("")
    add(
        "A site that fits no known project is not a false alarm. Nobody has shown what it is. "
        "The count says how many sites a reviewer would be sent."
    )
    add("")

    add("## Every signal tied to a known project")
    add("")
    rows = []
    for o in outcomes:
        for s in o.signals:
            r = by_id[s.signal_id]
            rows.append(
                (
                    s.available_on.isoformat(),
                    f"`{o.project.key}`",
                    TYPE_NAMES[s.signal_type],
                    RULE_NAMES[r.rule],
                    r.reference,
                    match(s, o.project, result.scoring.clustering),
                    "; ".join(r.named_by),
                )
            )
    add_all(
        _table(
            ("Seen", "Project", "Kind", "Strongest reason", "Record", "Tied by", "Name found"),
            sorted(rows),
        )
    )
    add("")

    add("## How a signal's day was set")
    add("")
    basis = Counter(r.seen_basis for r in history.records)
    add_all(_table(("A signal counts from", "Signals"), basis.most_common()))
    add("")
    add(
        "Where the day a record was posted is not kept, the later day is used. A lead time "
        "here is never longer than the records support."
    )
    add("")
    return "\n".join(lines)
