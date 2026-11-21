"""The inventory of Texas public bodies and where each posts its agendas. BUILD_PLAN.md M8.

config/tx_agenda_inventory.csv has one row per body: a commissioners court, a city council, a
planning body or a development corporation in the 30 test counties. It records the page where
the body's agendas are posted and the platform behind that page.

The inventory is research, done by reading each government's own website. It is not a
collector and it fetches nothing. A row says what a person saw on the date in the file's
header. Every platform still needs its terms and robots rules read before any collector is
written for it (BUILD_PLAN.md section 6).

A platform is named from an address, never from a guess. `platform_of` holds the rule for each
one, and the loader refuses a row whose platform its own addresses contradict.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pipeline.config import CONFIG_DIR, load_counties

INVENTORY = CONFIG_DIR / "tx_agenda_inventory.csv"
PLACES = CONFIG_DIR / "tx_places.csv"

BodyType = Literal[
    "commissioners_court", "city_council", "planning_body", "development_corporation"
]
Status = Literal["seen", "inferred", "not_found"]

# An outside meeting platform, recognized by the host or path of an agenda address.
_BY_ADDRESS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("civicplus_agendacenter", re.compile(r"/agendacenter(?:[/?#]|$)", re.I)),
    ("civicclerk", re.compile(r"^[^/]*civicclerk\.com", re.I)),
    ("legistar", re.compile(r"^[^/]*legistar\.com", re.I)),
    # Swagit keeps agenda files on a host under its owner's name. It comes before Granicus.
    ("swagit", re.compile(r"^[^/]*swagit\.com|^swagit-attachments\.granicus\.com", re.I)),
    ("granicus", re.compile(r"^[^/]*granicus\.com", re.I)),
    (
        "municode_meetings",
        re.compile(
            # The third host is where Municode Meetings stores the agenda files themselves.
            r"^[^/]*(?:municodemeetings\.com|meetings\.municode\.com)"
            r"|^mccmeetings\.blob\.core\.usgovcloudapi\.net",
            re.I,
        ),
    ),
    ("boarddocs", re.compile(r"^[^/]*boarddocs\.com", re.I)),
    ("novusagenda", re.compile(r"^[^/]*novusagenda\.com", re.I)),
    ("primegov", re.compile(r"^[^/]*primegov\.com", re.I)),
    ("escribe", re.compile(r"^[^/]*escribemeetings\.com", re.I)),
    ("iqm2", re.compile(r"^[^/]*iqm2\.com", re.I)),
    ("civicweb", re.compile(r"^[^/]*civicweb\.net", re.I)),
    ("destiny_hosted", re.compile(r"^[^/]*destinyhosted\.com", re.I)),
)
# A Texas county site run on the county association's shared hosting.
_COUNTY_SITE = re.compile(r"^(?:www\.)?co\.[a-z-]+\.tx\.us$", re.I)

OUTSIDE = tuple(name for name, _ in _BY_ADDRESS)
# Agendas on the government's own site, or nowhere, or not worked out.
OTHER = (
    "cira_county_site",
    "own_site_files",
    "other",
    "none_online",
    "no_website",
    "not_determined",
)
PLATFORMS = OUTSIDE + OTHER
# Platforms that mean a list of agendas was found.
FOUND = OUTSIDE + ("cira_county_site", "own_site_files", "other")


def _host_and_path(url: str) -> str:
    parts = urlsplit(url.strip())
    return f"{parts.netloc}{parts.path}"


def platform_of(url: str) -> str | None:
    """The outside platform an address belongs to, or None if the address names none.

    None does not mean the government's own site. It means this address alone does not say.
    """
    if not url:
        return None
    target = _host_and_path(url)
    for name, pattern in _BY_ADDRESS:
        if pattern.search(target):
            return name
    return None


def is_county_site(url: str) -> bool:
    return bool(url) and bool(_COUNTY_SITE.match(urlsplit(url.strip()).netloc))


_URL = r"^(https?://\S+)?$"


class AgendaBody(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    government: str = Field(min_length=3)
    counties: tuple[str, ...] = Field(min_length=1)
    body: str = Field(min_length=3)
    body_type: BodyType
    official_site: str = Field(pattern=_URL)
    agenda_url: str = Field(pattern=_URL)
    platform: str
    evidence: str
    status: Status
    notes: str

    @model_validator(mode="after")
    def _consistent(self) -> AgendaBody:
        where = f"{self.body}: "
        if self.platform not in PLATFORMS:
            raise ValueError(f"{where}unknown platform {self.platform!r}")
        found = self.platform in FOUND
        if found and not self.agenda_url:
            raise ValueError(f"{where}platform {self.platform} with no agenda address")
        if found and self.status == "not_found":
            raise ValueError(f"{where}platform {self.platform} with status not_found")
        if not found and self.status != "not_found":
            raise ValueError(f"{where}{self.platform} must have status not_found")
        if self.platform == "no_website" and (self.official_site or self.agenda_url):
            raise ValueError(f"{where}no_website with an address")
        if self.platform in ("not_determined", "other") and not self.notes.strip():
            raise ValueError(f"{where}{self.platform} needs a note saying why or what")
        # The platform must follow from the row's own addresses.
        named = {platform_of(self.agenda_url), platform_of(self.evidence)} - {None}
        if self.platform in OUTSIDE and self.platform not in named:
            raise ValueError(f"{where}no address on the row shows {self.platform}")
        if self.platform in ("own_site_files", "cira_county_site", "other"):
            agenda_names = platform_of(self.agenda_url)
            if agenda_names:
                raise ValueError(f"{where}the agenda address is a {agenda_names} address")
        if self.platform == "cira_county_site" and not is_county_site(self.agenda_url):
            raise ValueError(f"{where}cira_county_site needs a co.<name>.tx.us agenda address")
        return self


COLUMNS = (
    "government",
    "counties",
    "body",
    "body_type",
    "official_site",
    "agenda_url",
    "platform",
    "evidence",
    "status",
    "notes",
)


def _data_lines(path: Path) -> list[str]:
    return [
        line
        for line in path.read_text(encoding="utf-8").splitlines(keepends=True)
        if not line.startswith("#")
    ]


def load_inventory(path: Path | None = None) -> list[AgendaBody]:
    """Every body in the inventory. Raises on a row that breaks a rule."""
    reader = csv.DictReader(_data_lines(path or INVENTORY))
    if tuple(reader.fieldnames or ()) != COLUMNS:
        raise ValueError(f"inventory columns are {reader.fieldnames}, expected {COLUMNS}")
    scope = {c.name for c in load_counties("TX").counties}
    bodies = []
    for row in reader:
        counties = tuple(c.strip() for c in row["counties"].split(";") if c.strip())
        outside = [c for c in counties if c not in scope]
        if outside:
            raise ValueError(f"{row['body']}: {outside} is not one of the 30 counties")
        bodies.append(AgendaBody(**{**row, "counties": counties}))
    return bodies


def load_places(path: Path | None = None) -> list[tuple[str, tuple[str, ...]]]:
    """Every incorporated place in the 30 counties, with the test counties it lies in."""
    reader = csv.DictReader(_data_lines(path or PLACES))
    return [(row["place"], tuple(c.strip() for c in row["counties"].split(";"))) for row in reader]


PLATFORM_TERMS = CONFIG_DIR / "tx_agenda_platforms.csv"
PlatformStatus = Literal["restricted", "candidate", "not_read", "cleared"]


class PlatformTerms(BaseModel):
    """What one platform's own rules say about a program reading it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    platform: str
    vendor: str = Field(min_length=2)
    status: PlatformStatus
    robots: Literal["allowed", "disallowed", "none", "unreadable", "mixed", "not_read"]
    checked_on: str = Field(pattern=r"^(\d{4}-\d{2}-\d{2})?$")
    terms_url: str = Field(pattern=_URL)
    note: str = Field(min_length=10)

    @model_validator(mode="after")
    def _consistent(self) -> PlatformTerms:
        if self.platform not in FOUND:
            raise ValueError(f"{self.platform} is not a platform agendas can be found on")
        read = self.status != "not_read"
        if read != bool(self.checked_on):
            raise ValueError(f"{self.platform}: a status other than not_read needs the date read")
        if self.status == "cleared" and self.robots in ("disallowed", "unreadable", "not_read"):
            raise ValueError(f"{self.platform}: cleared, with a robots file that does not allow it")
        return self


def load_platform_terms(path: Path | None = None) -> dict[str, PlatformTerms]:
    """Every platform's standing, by name. Every platform agendas are found on must be listed."""
    reader = csv.DictReader(_data_lines(path or PLATFORM_TERMS))
    terms = {row["platform"]: PlatformTerms(**row) for row in reader}
    missing = sorted(set(FOUND) - set(terms))
    if missing:
        raise ValueError(f"platforms with no entry in the terms file: {missing}")
    return terms


SITE_TERMS = CONFIG_DIR / "tx_agenda_site_terms.csv"


def load_site_terms(path: Path | None = None) -> list[dict[str, str]]:
    """What each government's own site says about a program reading it, one row per host."""
    return list(csv.DictReader(_data_lines(path or SITE_TERMS)))


def summary(bodies: list[AgendaBody]) -> str:
    """Counts a person can read: bodies and governments by platform, and counties reached."""
    import collections

    primary = [b for b in bodies if b.body_type in ("commissioners_court", "city_council")]
    by_platform = collections.Counter(b.platform for b in bodies)
    governments = collections.Counter(b.platform for b in primary)
    counties: dict[str, set[str]] = collections.defaultdict(set)
    for b in primary:
        counties[b.platform].update(b.counties)
    lines = [
        f"{len(bodies)} bodies of {len(primary)} governments",
        "",
        f"{'platform':<24}{'bodies':>8}{'governments':>13}{'counties':>10}",
    ]
    for platform, count in by_platform.most_common():
        lines.append(
            f"{platform:<24}{count:>8}{governments[platform]:>13}{len(counties[platform]):>10}"
        )
    by_type = collections.Counter(b.body_type for b in bodies)
    by_status = collections.Counter(b.status for b in bodies)
    lines += ["", "by kind of body: " + ", ".join(f"{k} {v}" for k, v in sorted(by_type.items()))]
    lines += ["by status: " + ", ".join(f"{k} {v}" for k, v in sorted(by_status.items()))]
    return "\n".join(lines)


if __name__ == "__main__":
    print(summary(load_inventory()))
