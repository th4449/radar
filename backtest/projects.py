"""The list of known projects the backtest judges. BUILD_PLAN.md milestone M9.

One row per data center project in a test county, with two dates and the source of each.

- `news_date` is the earliest news report or company announcement found that calls the
  project a data center. **It is the date the project became public.** The owner settled
  that on November 22, 2026.
- `record_date` is the earliest dated record of any kind found: a county notice, minutes, a
  permit review, a petition. A government record is one of the things the radar reads, so it
  is a signal and never the public date.

The list is research, done by reading news sites and public records. A date here is the
earliest found, not the earliest that exists. This module reads the file and refuses a row
that breaks a rule. It fetches nothing.
"""

from __future__ import annotations

import csv
import datetime as dt
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backtest.harness import Project
from pipeline.config import load_counties

KNOWN_PROJECTS_TX = Path(__file__).parent / "known_projects_tx.csv"

COLUMNS = (
    "key",
    "name",
    "county",
    "place",
    "status",
    "crypto",
    "companies",
    "code_names",
    "lat",
    "lon",
    "record_date",
    "record_kind",
    "record_url",
    "record_read",
    "news_date",
    "news_outlet",
    "news_url",
    "news_read",
    "confidence",
    "notes",
)

Status = Literal["proposed", "approved", "under_construction", "operating", "cancelled", "unclear"]
# How far a cited page was checked. `second_read` was opened twice, the second time by the
# session that owns the list. `first_read` was opened by a research pass only. `not_opened`
# is known from a headline, an excerpt or another source. `set_aside` was read against a block
# and is not used. `none_found` means there is none.
Read = Literal["second_read", "first_read", "not_opened", "set_aside", "none_found"]

# Records a government made or posted. Each is a kind of record the radar could read.
GOVERNMENT_KINDS = frozenset(
    {
        "county_notice",
        "county_agenda",
        "county_minutes",
        "county_meeting",
        "county_hearing",
        "city_agenda",
        "city_minutes",
        "zoning_case",
        "state_air_permit_review",
        "state_filing",
    }
)
OTHER_KINDS = frozenset(
    {"petition", "official_statement", "company_release", "development_district_release", "news"}
)
RECORD_KINDS = GOVERNMENT_KINDS | OTHER_KINDS

_URL = r"^(https?://\S+)?$"
# Texas, with a margin. A point outside it is a typing mistake.
_LAT = (25.5, 36.8)
_LON = (-107.0, -93.3)


def _slug(county: str) -> str:
    return county.lower().replace(" ", "-")


class KnownProject(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)+$")
    name: str = Field(min_length=3)
    county: str
    place: str
    status: Status
    crypto: Literal["", "yes"]
    companies: tuple[str, ...]
    code_names: tuple[str, ...]
    lat: float | None
    lon: float | None
    record_date: dt.date | None
    record_kind: str
    record_url: str = Field(pattern=_URL)
    record_read: Read
    news_date: dt.date | None
    news_outlet: str
    news_url: str = Field(pattern=_URL)
    news_read: Read
    confidence: Literal["high", "medium", "low"]
    notes: str

    @model_validator(mode="after")
    def _consistent(self) -> KnownProject:
        where = f"{self.key}: "
        if not self.key.startswith(_slug(self.county) + "-"):
            raise ValueError(f"{where}the key must start with {_slug(self.county)}-")
        if self.record_kind and self.record_kind not in RECORD_KINDS:
            raise ValueError(f"{where}unknown record_kind {self.record_kind!r}")
        if self.record_url and not self.record_kind:
            raise ValueError(f"{where}a record address with no record_kind")
        for side, date, url, read in (
            ("record", self.record_date, self.record_url, self.record_read),
            ("news", self.news_date, self.news_url, self.news_read),
        ):
            if date and not url:
                raise ValueError(f"{where}{side}_date with no address for its source")
            if read in ("none_found", "set_aside") and (date or url):
                raise ValueError(f"{where}{side}_read is {read}, with a date or an address")
        if (self.lat is None) != (self.lon is None):
            raise ValueError(f"{where}a point needs both lat and lon")
        if self.lat is not None and self.lon is not None:
            inside = _LAT[0] <= self.lat <= _LAT[1] and _LON[0] <= self.lon <= _LON[1]
            if not inside:
                raise ValueError(f"{where}the point is outside Texas")
        return self

    @property
    def public_date(self) -> dt.date | None:
        """The day the project became public: the first news report or company announcement."""
        return self.news_date

    @property
    def government_record_lead_days(self) -> int | None:
        """Days a government record came before the first news report. None if it cannot be said.

        Not a measured lead time. Both dates are the earliest found.
        """
        if self.record_kind not in GOVERNMENT_KINDS or not self.record_date or not self.news_date:
            return None
        return (self.news_date - self.record_date).days


def _split(cell: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in cell.split(";") if part.strip())


def _data_lines(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as lines:
        return [line for line in lines if not line.startswith("#")]


def load_known_projects(path: Path = KNOWN_PROJECTS_TX) -> list[KnownProject]:
    """Every project in the file. Raises on a row that breaks a rule."""
    reader = csv.DictReader(_data_lines(path))
    if tuple(reader.fieldnames or ()) != COLUMNS:
        raise ValueError(f"the columns are {reader.fieldnames}, expected {COLUMNS}")
    scope = {c.name for c in load_counties("TX").counties}
    projects: list[KnownProject] = []
    seen: set[str] = set()
    for raw in reader:
        if raw["county"] not in scope:
            raise ValueError(f"{raw['key']}: {raw['county']} is not one of the 30 counties")
        if raw["key"] in seen:
            raise ValueError(f"{raw['key']} is listed twice")
        seen.add(raw["key"])
        for column in ("record_date", "news_date"):
            if raw[column] and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw[column]):
                raise ValueError(f"{raw['key']}: {column} {raw[column]!r} is not YYYY-MM-DD")
        projects.append(
            KnownProject(
                **{
                    **raw,
                    "companies": _split(raw["companies"]),
                    "code_names": _split(raw["code_names"]),
                    **{c: raw[c] or None for c in ("lat", "lon", "record_date", "news_date")},
                }
            )
        )
    return projects


def to_project(known: KnownProject, entity_ids: frozenset[int] = frozenset()) -> Project:
    """The project as the harness judges it. Company ids come from the database's entities."""
    fips = {c.name: c.fips for c in load_counties("TX").counties}
    point = None if known.lat is None or known.lon is None else (known.lon, known.lat)
    return Project(
        key=known.key,
        name=known.name,
        county_fips=fips[known.county],
        public_date=known.public_date,
        entity_ids=entity_ids,
        names=frozenset(known.code_names),
        point=point,
    )
