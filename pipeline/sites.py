"""Group stored signals into sites and score every site. See BUILD_PLAN.md milestone M5.

Run after processing, and once a day even when nothing new arrived, because scores decay.

- A signal with a county joins the site it fits, or starts one. See pipeline/cluster.py.
- A signal with no county stays off every site. Its record does not say where it is.
- Every site is scored again from all its signals. See pipeline/score.py.
- A candidate site at or above the review threshold moves into the reviewers' queue. That is
  the only status change made here, and the database refuses any other from a job.
- A site is never deleted, merged or split here, and a signal never leaves a site.
"""

from __future__ import annotations

import datetime as dt
import json

import psycopg

from pipeline.cluster import Group, Item, assign
from pipeline.config import ScoringFile, load_scoring
from pipeline.counties import CountyIndex
from pipeline.score import Scored, score_site

STATES = {"48": "TX", "26": "MI"}


def _names(extracted: dict) -> frozenset[str]:
    """Project code names and project numbers stored with a signal."""
    names = {
        r["term"]
        for r in extracted.get("reasons") or []
        if r.get("rule") == "project_code_name" and r.get("term")
    }
    names |= set(extracted.get("project_numbers") or [])
    return frozenset(names)


def _point(extracted: dict) -> tuple[float, float] | None:
    point = extracted.get("point")
    if not isinstance(point, dict):
        return None
    try:
        return float(point["lon"]), float(point["lat"])
    except (KeyError, TypeError, ValueError):
        return None


def _label(group: Group, entity_names: dict[int, str]) -> str:
    """What a new site is called: who or what its first signal names, and the county."""
    state = STATES[group.county_fips[:2]]
    county = CountyIndex.for_state(state).name(group.county_fips) or group.county_fips
    for member in group.members:
        if member.entity_id is not None:
            return f"{entity_names[member.entity_id]}, {county} County"
    for member in group.members:
        if member.names:
            return f"{sorted(member.names)[0]}, {county} County"
    return f"Unnamed site, {county} County"


def _centroid(members: list[Item]) -> tuple[float, float] | None:
    points = [m.point for m in members if m.point is not None]
    if not points:
        return None
    return sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)


def update_sites(
    conn: psycopg.Connection,
    *,
    as_of: dt.date | None = None,
    scoring: ScoringFile | None = None,
) -> dict:
    scoring = scoring or load_scoring()
    as_of = as_of or dt.datetime.now(dt.UTC).date()

    site_county = dict(conn.execute("select id, county_fips from public.sites").fetchall())
    rows = conn.execute(
        """select sg.id, sg.site_id, sg.county_fips, sg.entity_id, sg.event_date, sg.signal_type,
                  sg.confidence, sg.extracted, src.slug, e.name
           from public.signals sg
           join public.documents d on d.id = sg.document_id
           join public.sources src on src.id = d.source_id
           left join public.entities e on e.id = sg.entity_id
           order by sg.id"""
    ).fetchall()

    entity_names: dict[int, str] = {}
    scored: dict[int, Scored] = {}
    groups: dict[int, Group] = {}
    waiting: list[Item] = []
    summary = {"as_of": as_of.isoformat(), "unplaced": 0, "outside_states": 0}
    for signal_id, site_id, fips, entity_id, day, kind, confidence, extracted, slug, name in rows:
        if entity_id is not None:
            entity_names[entity_id] = name
        scored[signal_id] = Scored(
            kind, day, None if confidence is None else float(confidence), slug, signal_id
        )
        county = site_county[site_id] if site_id is not None else fips
        if county is None:
            summary["unplaced"] += 1  # the record gives no county
            continue
        if county[:2] not in STATES:
            summary["outside_states"] += 1
            continue
        item = Item(signal_id, county, entity_id, _point(extracted), _names(extracted), day)
        if site_id is None:
            waiting.append(item)
        else:
            groups.setdefault(site_id, Group(site_id, county, [])).members.append(item)

    plan = assign(waiting, groups.values(), scoring.clustering)

    # New sites, oldest first, then every waiting signal onto its site.
    stored_key: dict[int | str, int] = {key: key for key in groups}
    for group in plan.new_sites:
        center = _centroid(group.members)
        stored_key[group.key] = conn.execute(
            """insert into public.sites (state, county_fips, label, geom)
               values (%s, %s, %s,
                       case when %s::float8 is null then null
                            else extensions.st_setsrid(
                                   extensions.st_makepoint(%s::float8, %s::float8), 4326) end)
               returning id""",
            [
                STATES[group.county_fips[:2]], group.county_fips, _label(group, entity_names),
                center[0] if center else None, center[0] if center else None,
                center[1] if center else None,
            ],
        ).fetchone()[0]  # fmt: skip
        groups[stored_key[group.key]] = Group(stored_key[group.key], group.county_fips, [])
    by_id = {item.signal_id: item for item in waiting}
    for signal_id, key in plan.attach.items():
        site_id = stored_key[key]
        link = plan.reasons.get(signal_id) or "the first signal of this site"
        conn.execute(
            """update public.signals
               set site_id = %s, extracted = extracted || jsonb_build_object('site_link', %s::text)
               where id = %s and site_id is null""",
            [site_id, link, signal_id],
        )
        groups[site_id].members.append(by_id[signal_id])

    # Score every site that has signals.
    moved = 0
    threshold = scoring.thresholds.review_threshold
    for site_id, group in sorted(groups.items()):
        result = score_site([scored[m.signal_id] for m in group.members], as_of, scoring)
        first = min(m.event_date for m in group.members)
        center = _centroid(group.members)
        before, after = conn.execute(
            """with old as (select status from public.sites where id = %(id)s)
               update public.sites s
               set score = %(score)s, score_detail = %(detail)s::jsonb, scored_at = now(),
                   first_signal_at = %(first)s,
                   geom = case when %(lon)s::float8 is null then s.geom
                               else extensions.st_setsrid(
                                      extensions.st_makepoint(%(lon)s::float8, %(lat)s::float8),
                                      4326) end,
                   status = case when s.status = 'candidate' and %(score)s >= %(threshold)s
                                 then 'in_review' else s.status end
               from old where s.id = %(id)s
               returning old.status, s.status""",
            {
                "id": site_id,
                "score": result.score,
                "detail": json.dumps(result.detail()),
                "first": dt.datetime.combine(first, dt.time(), dt.UTC),
                "lon": center[0] if center else None,
                "lat": center[1] if center else None,
                "threshold": threshold,
            },
        ).fetchone()
        moved += before != after

    summary |= {
        "sites_new": len(plan.new_sites),
        "signals_attached": len(plan.attach),
        "unanchored": len(plan.unanchored),
        "sites_scored": len(groups),
        "moved_to_review": moved,
        "possible_same_site": [
            {"signal_id": signal_id, "sites": [stored_key[k] for k in keys]}
            for signal_id, keys in plan.possible_same_site
        ],
        "placeholder_scoring": scoring.placeholder,
    }
    return summary
