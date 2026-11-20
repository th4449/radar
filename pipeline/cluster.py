"""Which signals are one site. See BUILD_PLAN.md milestone M5 and config/scoring.yaml.

A site is a place or a project in one county. Signals join only inside a county, and only for a
reason that can be said in a few words:

- they name the same company, unless both have coordinates that are far apart,
- they have coordinates close to each other, whoever they name, or
- they carry the same project name or number.

A signal with no company, no coordinates and no project name has nothing to hold it to a place.
It makes no site.

Sites are never rearranged. A signal already on a site stays there, because a reviewer may have
acted on that site. A new signal joins the site it fits. If it fits two, it joins the older one
and both are flagged for a person to look at.

Signals are taken oldest first, so the same signals always give the same sites. Nothing in this
module touches the database.
"""

from __future__ import annotations

import datetime as dt
import math
from collections.abc import Iterable
from dataclasses import dataclass, field

from pipeline.config import Clustering

Point = tuple[float, float]  # longitude, latitude
_EARTH_M = 6_371_000.0


@dataclass(frozen=True)
class Item:
    """A signal, as clustering sees it. It always has a county."""

    signal_id: int
    county_fips: str
    entity_id: int | None
    point: Point | None
    names: frozenset[str]  # project code names and project numbers
    event_date: dt.date

    @property
    def anchored(self) -> bool:
        return self.entity_id is not None or self.point is not None or bool(self.names)


@dataclass
class Group:
    """A site and the signals on it. key is the site's id, or "new-1" for one not stored yet."""

    key: int | str
    county_fips: str
    members: list[Item]


@dataclass
class Plan:
    attach: dict[int, int | str] = field(default_factory=dict)  # signal id -> site key
    reasons: dict[int, str] = field(default_factory=dict)  # why a signal joined a site
    new_sites: list[Group] = field(default_factory=list)
    unanchored: list[int] = field(default_factory=list)
    possible_same_site: list[tuple[int, list[int | str]]] = field(default_factory=list)


def distance_m(a: Point, b: Point) -> float:
    """Great-circle distance in meters."""
    lon1, lat1, lon2, lat2 = (math.radians(v) for v in (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * _EARTH_M * math.asin(math.sqrt(h))


def _nearest(item: Item, group: Group) -> float | None:
    if item.point is None:
        return None
    distances = [distance_m(item.point, m.point) for m in group.members if m.point is not None]
    return min(distances) if distances else None


def _link(item: Item, group: Group, rules: Clustering) -> str | None:
    """Why the signal belongs on the site, or None."""
    if item.county_fips != group.county_fips:
        return None
    if item.names and any(item.names & m.names for m in group.members):
        return "the same project name or number"
    nearest = _nearest(item, group)
    same_company = item.entity_id is not None and any(
        m.entity_id == item.entity_id for m in group.members
    )
    if same_company and (nearest is None or nearest <= rules.same_company_m):
        return "the same company"
    if nearest is not None and nearest <= rules.near_m:
        return f"coordinates within {rules.near_m:g} m"
    return None


def assign(new_items: Iterable[Item], sites: Iterable[Group], rules: Clustering) -> Plan:
    plan = Plan()
    sites = list(sites)
    already = {m.signal_id for g in sites for m in g.members}
    groups = [Group(g.key, g.county_fips, list(g.members)) for g in sites]
    pending = sorted(new_items, key=lambda i: (i.event_date, i.signal_id))
    plan.unanchored = [i.signal_id for i in pending if not i.anchored]
    pending = [i for i in pending if i.anchored]

    # A signal can tie together two new groups that had nothing in common until it arrived.
    # Those groups then become one. Stored sites are never merged.
    made: list[Group] = []
    for item in pending:
        linked = [g for g in (*groups, *made) if _link(item, g, rules)]
        stored = sorted((g for g in linked if isinstance(g.key, int)), key=lambda g: g.key)
        fresh = [g for g in linked if not isinstance(g.key, int)]
        if stored:
            target = stored[0]
            if len(stored) > 1:
                plan.possible_same_site.append((item.signal_id, [g.key for g in stored]))
        elif fresh:
            target = fresh[0]
        else:
            target = Group(f"new-{len(made) + 1}", item.county_fips, [])
            made.append(target)
        if linked:
            plan.reasons[item.signal_id] = _link(item, target, rules) or ""
        target.members.append(item)
        for other in fresh:
            if other is not target:
                target.members.extend(other.members)
                made.remove(other)

    for number, group in enumerate(
        sorted(made, key=lambda g: min((m.event_date, m.signal_id) for m in g.members)), start=1
    ):
        group.key = f"new-{number}"
        group.members.sort(key=lambda m: (m.event_date, m.signal_id))
        plan.new_sites.append(group)
    for group in (*groups, *plan.new_sites):
        for member in group.members:
            plan.attach[member.signal_id] = group.key
    # Signals that were already on a site are not part of the plan.
    for signal_id in already:
        plan.attach.pop(signal_id, None)
    plan.possible_same_site.sort()
    return plan
