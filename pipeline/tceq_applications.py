"""Where a TCEQ air permit application says its site is. See docs/sources.

The two TCEQ lists give no county, so an air permit signal cannot join a site. Each row links
its application file, and that file states the county. This module fetches the file for a row
that became a signal, and for no other row, and reads three kinds of line from it:

- the address block of TCEQ's online form: street, city, ZIP, county, latitude, longitude,
- the reference block at the head of TCEQ's letters: "Midlothian, Ellis County", and
- the county line of a technical review sheet.

Every line found must name the same county. If two disagree, the file is ambiguous and the
signal gets no county. Nothing is taken from running text, because a long application names
many counties in passing.

The file is fetched once through the shared fetcher, archived like any document and reused.
It holds the names of company and agency staff, so it is stored restricted. Only the address
lines are copied to the signal.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import psycopg

from collectors.base import (
    Blocked,
    FetchError,
    NotPermitted,
    RobotsDisallowed,
    Sink,
    TooLarge,
)
from pipeline.config import Source
from pipeline.counties import CountyIndex

SOURCE_ID = "tx_tceq_air_pending_legacy"
MAX_FILES_PER_RUN = 25
_TX_BOX = (-107.0, 25.5, -93.0, 37.0)

Status = Literal["read", "no_county", "ambiguous"]

# TCEQ's online form, as its text comes out of the file.
_FORM = re.compile(
    r"^Number and Street (?P<street>[^\n]+)\n"
    r"City (?P<city>[^\n]+)\n"
    r"State TX\n"
    r"ZIP (?P<zip>\d{5})(?:-\d{4})?\n"
    r"County (?P<county>[^\n]+)$"
    r"(?:\nLatitude[^\n]*? (?P<lat>-?\d{1,3}\.\d+)\nLongitude[^\n]*? (?P<lon>-?\d{1,3}\.\d+)$)?",
    re.MULTILINE,
)
# The head of a TCEQ letter: the city and county, then the customer or entity number.
_LETTER = re.compile(
    r"^(?P<city>[A-Z][A-Za-z .'-]{1,40}), (?P<county>[A-Z][A-Za-z ]{2,30}) County\n"
    r"(?:Customer Reference Number|Regulated Entity Number)",
    re.MULTILINE,
)
_REVIEW = re.compile(r"^County: ?\.{3,} ?(?P<county>[A-Za-z ]+?) Region:", re.MULTILINE)
_NAICS = re.compile(r"^Primary NAICS Code (\d{2,6})$", re.MULTILINE)
_BUSINESS = re.compile(r"^What is the primary business of this entity\? ([^\n]+)$", re.MULTILINE)


@dataclass(frozen=True)
class ApplicationSite:
    status: Status
    county: str | None = None
    county_fips: str | None = None
    in_scope: bool = False
    city: str | None = None
    street: str | None = None
    zip: str | None = None
    lon: float | None = None
    lat: float | None = None
    naics: str | None = None
    primary_business: str | None = None
    evidence: tuple[str, ...] = ()  # the lines the county was read from
    counties_read: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "county": self.county,
            "county_fips": self.county_fips,
            "in_scope": self.in_scope,
            "city": self.city,
            "street": self.street,
            "zip": self.zip,
            "naics": self.naics,
            "primary_business": self.primary_business,
            "evidence": list(self.evidence),
            "counties_read": list(self.counties_read),
        }


def _coordinates(lat_text: str | None, lon_text: str | None) -> tuple[float, float] | None:
    if not lat_text or not lon_text:
        return None
    lat, lon = float(lat_text), float(lon_text)
    # The form asks for a west longitude with a minus sign. Applicants often leave it off.
    if lon > 0:
        lon = -lon
    west, south, east, north = _TX_BOX
    return (lon, lat) if west <= lon <= east and south <= lat <= north else None


def read_application(text: str, counties: CountyIndex) -> ApplicationSite:
    """What the file states about the site. The county only when every line agrees."""
    found: dict[str, tuple[str, str, bool]] = {}
    evidence: list[str] = []
    for pattern in (_FORM, _LETTER, _REVIEW):
        for m in pattern.finditer(text):
            county = counties.lookup(m.group("county"))
            if county is None:
                continue
            found[county[1]] = county
            if pattern is _LETTER:
                line = m.group(0).split("\n")[0]  # "Midlothian, Ellis County"
            else:
                line = f"County {m.group('county').strip()}"
            if line not in evidence:
                evidence.append(line)

    form = _FORM.search(text)
    letter = _LETTER.search(text)
    point = _coordinates(form.group("lat"), form.group("lon")) if form else None
    naics, business = _NAICS.search(text), _BUSINESS.search(text)
    common = {
        "city": (form.group("city") if form else letter.group("city") if letter else None),
        "street": form.group("street") if form else None,
        "zip": form.group("zip") if form else None,
        "lon": point[0] if point else None,
        "lat": point[1] if point else None,
        "naics": naics.group(1) if naics else None,
        "primary_business": business.group(1).strip() if business else None,
        "evidence": tuple(evidence[:10]),
        "counties_read": tuple(sorted(c[0] for c in found.values())),
    }
    if not found:
        return ApplicationSite("no_county", **common)
    if len(found) > 1:
        return ApplicationSite("ambiguous", **common)
    name, fips, in_scope = next(iter(found.values()))
    return ApplicationSite("read", name, fips, in_scope, **common)


# --- fetching the files for the signals that need them ------------------------------------------


def enrich_air_permits(
    conn: psycopg.Connection,
    *,
    source: Source,
    lookup: Callable[[str], bytes],
    sink: Sink,
    counties: CountyIndex | None = None,
    limit: int = MAX_FILES_PER_RUN,
) -> dict:
    """Give each air permit signal that has no county the one its application file states.

    lookup fetches a URL once, archives the answer and answers from the archive after that.
    """
    counties = counties or CountyIndex.for_state("TX")
    waiting = conn.execute(
        """select id, extracted->'row'->>'application_url'
           from public.signals
           where signal_type = 'air_permit' and county_fips is null
             and extracted->'row'->>'application_url' is not null
             and (extracted->'application' is null
                  or extracted->'application'->>'status' = 'fetch_failed'
                  or extracted->'application'->>'url'
                     is distinct from extracted->'row'->>'application_url')
           order by id
           limit %s""",
        [limit],
    ).fetchall()
    summary: dict = {
        "asked": 0, "read": 0, "in_scope": 0, "out_of_scope": 0, "no_county": 0,
        "ambiguous": 0, "too_large": 0, "fetch_failed": 0,
    }  # fmt: skip
    for signal_id, url in waiting:
        summary["asked"] += 1
        record: dict = {"url": url}
        point = None
        try:
            lookup(url)
        except (Blocked, RobotsDisallowed, NotPermitted) as exc:
            # A refusal ends this step. A person decides what happens next.
            summary["asked"] -= 1
            summary["stopped"] = str(exc)
            break
        except TooLarge:
            record["status"] = "too_large"
        except FetchError as exc:
            record |= {"status": "fetch_failed", "error": str(exc)[:200]}
        else:
            stored = sink.find(source, url)
            site = read_application(stored.text, counties)
            record |= site.as_dict() | {
                "document_sha256": stored.sha256,
                "read_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
            }
            if site.lon is not None:
                point = {
                    "lon": site.lon,
                    "lat": site.lat,
                    "from": "the application file, as the applicant entered it",
                }
        status = record["status"]
        summary[status] += 1
        fips = record.get("county_fips") if record.get("in_scope") else None
        if status == "read":
            summary["in_scope" if fips else "out_of_scope"] += 1
        added = {"application": record} | ({"point": point} if point and fips else {})
        conn.execute(
            """update public.signals
               set county_fips = coalesce(%s, county_fips), extracted = extracted || %s::jsonb
               where id = %s""",
            [fips, json.dumps(added), signal_id],
        )
    return summary
