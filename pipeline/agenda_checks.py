"""Independent checks of the agenda inventory, and what each row has earned. BUILD_PLAN.md M8.

The inventory in config/tx_agenda_inventory.csv was written by one read of each government's
website. One read can be wrong. So nothing in it is trusted until a second, independent read
of the same page agrees.

config/tx_agenda_checks.csv is the record of those reads. A check holds observations only:
the address opened, the agenda addresses copied from the page, the newest agenda's date and
the bodies seen listed. The reader is never told what the inventory says and never names a
platform. This module names the platform from the copied addresses, with the same patterns
the inventory is held to, and compares.

    uv run python -m pipeline.agenda_checks            counts by verdict
    uv run python -m pipeline.agenda_checks --list     every row that needs a person, and why
    uv run python -m pipeline.agenda_checks --csv      the same list as a CSV to work through

Verdicts:

  confirmed          a check opened the row's page, its addresses show the row's platform, the
                     body was listed there and the newest agenda is recent
  agreed_none        both reads found no official website
  not_current        the platform and body agree, and the newest agenda is old or undated.
                     The government may have moved its agendas
  government_only    the platform agrees for the government. This body was not seen listed
  not_shown          the check read the page and saw no agenda addresses on it
  contradicted       the check saw something else: another platform, another state, a site
                     where the inventory says there is none
  unreadable         the page was empty, blocked or failed
  expired            the last check is older than RECHECK_DAYS
  unchecked          no check has opened this row's page
  undetermined       the inventory itself names no agenda page

A collector takes a row only when it is `confirmed` and its platform's own rules allow a
collector at all. See `collectable` and config/tx_agenda_platforms.csv.

Who made a check is recorded in `by`:

  second_read    a research pass, reading through a page-reading tool. It cannot run a page's
                 scripts, so a list that fills itself in comes back empty.
  browser_read   the builder opened the page in a real browser, which runs scripts
  hand           a person opened the page. Add a line to the checks file to record one.

The newest check of a page decides. On the same day a browser read outranks a second read and
a person outranks both.
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pipeline.agenda_inventory import (
    GOVERNING,
    OUTSIDE,
    AgendaBody,
    PlatformTerms,
    _data_lines,
    is_county_site,
    load_inventory,
    load_platform_terms,
    load_site_terms,
    platform_of,
)
from pipeline.config import CONFIG_DIR

CHECKS = CONFIG_DIR / "tx_agenda_checks.csv"
CHECKS_BY_STATE = {"TX": CHECKS, "MI": CONFIG_DIR / "mi_agenda_checks.csv"}

# A newest agenda older than this, on the day of the check, is not current.
CURRENT_DAYS = 400
# A check older than this no longer counts. Governments change platforms.
RECHECK_DAYS = 180

Kind = Literal["read_page", "find_site", "find_agendas"]
Result = Literal["read", "empty", "blocked", "error", "not_found"]
Verdict = Literal[
    "confirmed",
    "agreed_none",
    "not_current",
    "government_only",
    "not_shown",
    "contradicted",
    "unreadable",
    "expired",
    "unchecked",
    "undetermined",
]
# Verdicts that need nothing more from a person.
SETTLED = ("confirmed", "agreed_none")

_URL = r"^(https?://\S+)?$"
_KEYED = re.compile(r"[?&](resourcekey|key|token|apikey|access_token|sig|signature)=", re.I)
_SEP = " | "


class Check(BaseModel):
    """One independent read of one page, or one search for a site."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    government: str = Field(min_length=3)
    kind: Kind
    page: str = Field(pattern=_URL)  # the inventory's agenda address this read was sent to
    checked_on: dt.date
    by: Literal["second_read", "browser_read", "hand"]
    result: Result
    opened: str = Field(pattern=_URL)
    followed_to: str = Field(pattern=_URL)
    # Whether the page is for a place in the inventory's own state. A township's name is
    # often a town's name somewhere else.
    names_state: Literal["yes", "no", "unknown"]
    agenda_links: tuple[str, ...]
    # Dated agendas seen listed for the expected bodies. A page can list agendas that open by
    # script and so give no address to copy.
    agendas_listed: int = Field(ge=0)
    newest_agenda_date: dt.date | None
    bodies_listed: tuple[str, ...]
    other_hosts: tuple[str, ...]
    notes: str

    @model_validator(mode="after")
    def _sane(self) -> Check:
        where = f"{self.government}: "
        if self.kind == "read_page" and not self.page:
            raise ValueError(f"{where}a page read with no page")
        if self.result == "read" and not self.opened:
            raise ValueError(f"{where}read, with no address opened")
        for link in self.agenda_links:
            if not link.startswith(("http://", "https://")):
                raise ValueError(f"{where}agenda link {link!r} is not a web address")
        if self.agendas_listed < len(self.agenda_links):
            raise ValueError(f"{where}fewer agendas listed than agenda links copied")
        if self.newest_agenda_date and self.newest_agenda_date > self.checked_on + dt.timedelta(
            days=120
        ):
            raise ValueError(f"{where}newest agenda date is far in the future")
        if "@" in f"{self.notes} {' '.join(self.agenda_links)}":
            raise ValueError(f"{where}a check holds no email address")
        # A share key in a public link is not ours to republish, and a secret scanner stops on it.
        if _KEYED.search(" ".join((*self.agenda_links, self.opened, self.followed_to))):
            raise ValueError(f"{where}an address carries a key or token. Drop that part")
        return self

    def platforms_seen(self) -> set[str]:
        """Every outside platform the copied addresses show."""
        addresses = [*self.agenda_links, self.opened, self.followed_to]
        addresses += [f"https://{host}/" for host in self.other_hosts]
        return {p for p in map(platform_of, addresses) if p}

    def platforms_in_links(self) -> set[str]:
        return {p for p in map(platform_of, self.agenda_links) if p}


COLUMNS = (
    "government",
    "kind",
    "page",
    "checked_on",
    "by",
    "result",
    "opened",
    "followed_to",
    "names_state",
    "agenda_links",
    "agendas_listed",
    "newest_agenda_date",
    "bodies_listed",
    "other_hosts",
    "notes",
)
_LISTS = ("agenda_links", "bodies_listed", "other_hosts")


def load_checks(path: Path | None = None, state: str = "TX") -> list[Check]:
    path = path or CHECKS_BY_STATE[state]
    if not path.exists():
        return []
    reader = csv.DictReader(_data_lines(path))
    if tuple(reader.fieldnames or ()) != COLUMNS:
        raise ValueError(f"check columns are {reader.fieldnames}, expected {COLUMNS}")
    checks = []
    for row in reader:
        for name in _LISTS:
            row[name] = tuple(part.strip() for part in row[name].split(_SEP) if part.strip())
        row["newest_agenda_date"] = row["newest_agenda_date"] or None
        checks.append(Check(**row))
    return checks


def write_checks(checks: list[Check], path: Path, header: str = "") -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(header)
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(COLUMNS)
        for c in checks:
            data = c.model_dump()
            for name in _LISTS:
                data[name] = _SEP.join(data[name])
            data["checked_on"] = c.checked_on.isoformat()
            data["newest_agenda_date"] = (
                c.newest_agenda_date.isoformat() if c.newest_agenda_date else ""
            )
            writer.writerow([data[name] for name in COLUMNS])


def _key(url: str) -> str:
    return url.strip().rstrip("/").lower()


# On the same day a read in a real browser outranks a research pass, and a person outranks both.
_RANK = {"second_read": 0, "browser_read": 1, "hand": 2}


class Checks:
    """The checks, with the one that decides for each page."""

    def __init__(self, checks: list[Check]) -> None:
        self.all = checks
        order = sorted(checks, key=lambda c: (c.checked_on, _RANK[c.by]))
        self._page: dict[tuple[str, str], Check] = {}
        self._search: dict[tuple[str, Kind], Check] = {}
        for c in order:  # later ones replace earlier ones
            if c.kind == "read_page":
                self._page[(c.government, _key(c.page))] = c
            else:
                self._search[(c.government, c.kind)] = c

    def of_page(self, body: AgendaBody) -> Check | None:
        return self._page.get((body.government, _key(body.agenda_url)))

    def of_search(self, body: AgendaBody, kind: Kind) -> Check | None:
        return self._search.get((body.government, kind))


def verdict(body: AgendaBody, checks: Checks, today: dt.date) -> tuple[Verdict, str]:
    """What this row has earned, and the reason in a sentence."""
    primary = body.body_type in GOVERNING

    if body.platform == "no_website":
        check = checks.of_search(body, "find_site")
        if check is None:
            return "unchecked", "No second search was made for a website."
        if (today - check.checked_on).days > RECHECK_DAYS:
            return "expired", f"Last checked {check.checked_on}."
        if check.result == "read" and check.opened and check.names_state != "no":
            return "contradicted", f"A second search found a site: {check.opened}"
        return "agreed_none", "Two searches found no official website."

    if not body.agenda_url:
        check = checks.of_search(body, "find_agendas") if primary else None
        if check and check.result == "read" and check.agenda_links:
            return (
                "contradicted",
                f"The inventory names no agenda page. A second read found one: {check.opened}",
            )
        return "undetermined", "The inventory names no agenda page for this body."

    check = checks.of_page(body)
    if check is None:
        return "unchecked", "No check has opened this page."
    if (today - check.checked_on).days > RECHECK_DAYS:
        return "expired", f"Last checked {check.checked_on}."
    if check.result in ("empty", "blocked", "error"):
        return "unreadable", f"The check could not read the page: {check.result}. {check.notes}"
    if check.result == "not_found":
        return "contradicted", "The check found no such page."
    if check.names_state == "no":
        return "contradicted", "The page is for a place in another state."

    # Agreement rests on the agenda addresses the check copied, not on the page's own address:
    # an empty Agenda Center page has an Agenda Center address too.
    in_links = check.platforms_in_links()
    if body.platform == "not_determined":
        if check.agendas_listed:
            return "contradicted", "The inventory could not name a platform. The check saw agendas."
        return "undetermined", "Neither read could name where the agendas are."
    if check.agendas_listed == 0:
        return "not_shown", "The check read the page and saw no agendas listed on it."
    if body.platform in OUTSIDE:
        # With no address to copy, the page the agendas are listed on must itself be the platform's.
        where = in_links or {
            p for p in (platform_of(check.opened), platform_of(check.followed_to)) if p
        }
        if body.platform not in where:
            if where:
                return "contradicted", f"The check saw {', '.join(sorted(where))} addresses."
            return (
                "contradicted",
                f"The agendas the check saw are not on {body.platform} addresses.",
            )
    else:  # the government's own site, a county association site, or a platform named in notes
        if in_links:
            return "contradicted", f"The check saw {', '.join(sorted(in_links))} addresses."
        if body.platform == "cira_county_site" and not (
            any(is_county_site(link) for link in check.agenda_links)
            or (not check.agenda_links and is_county_site(check.opened))
        ):
            return "contradicted", "The agenda files are not on a county association site."

    if body.body not in check.bodies_listed:
        return "government_only", "The platform agrees. This body was not seen listed on the page."
    if check.newest_agenda_date is None:
        return "not_current", "The platform agrees. The check saw no date on the newest agenda."
    age = (check.checked_on - check.newest_agenda_date).days
    if age > CURRENT_DAYS:
        return "not_current", f"The newest agenda the check saw is from {check.newest_agenda_date}."
    return "confirmed", f"Checked {check.checked_on}. Newest agenda {check.newest_agenda_date}."


# What a government's own pages may say and still be read by a collector.
SITE_ALLOWS = ("own_pages_silent", "no_terms_found")


def site_allows(body: AgendaBody, sites: list[dict[str, str]]) -> bool:
    """True when the government's own terms were read and nothing in them stands against it."""
    for row in sites:
        if row["government"] == body.government and row["platform"] == body.platform:
            return row["result"] in SITE_ALLOWS
    return False  # not read is not allowed


def collectable(
    body: AgendaBody,
    checks: Checks,
    today: dt.date,
    platforms: dict[str, PlatformTerms] | None = None,
    sites: list[dict[str, str]] | None = None,
    state: str = "TX",
) -> bool:
    """True only when a collector may take this row. Three things must all hold.

    The row is right: an independent check confirmed it. The platform may be read: its own
    terms and robots rules were read, nothing in them stands against a collector, and the owner
    said to go ahead. And the government's own terms were read and say nothing against it.
    See config/tx_agenda_platforms.csv, which both states share, and each state's own
    site terms file: config/tx_agenda_site_terms.csv and config/mi_agenda_site_terms.csv.
    """
    platforms = load_platform_terms() if platforms is None else platforms
    terms = platforms.get(body.platform)
    if terms is None or terms.status != "cleared":
        return False
    if not site_allows(body, load_site_terms(state=state) if sites is None else sites):
        return False
    return verdict(body, checks, today)[0] == "confirmed"


def report(bodies: list[AgendaBody], checks: Checks, today: dt.date, listing: bool) -> str:
    verdicts = [(b, *verdict(b, checks, today)) for b in bodies]
    primary = [v for v in verdicts if v[0].body_type in GOVERNING]
    counts = collections.Counter(v[1] for v in verdicts)
    governments = collections.Counter(v[1] for v in primary)
    lines = [
        f"{len(bodies)} bodies, {len(checks.all)} checks on file, as of {today}",
        "",
        f"{'verdict':<18}{'bodies':>8}{'governments':>13}",
    ]
    for name, count in counts.most_common():
        lines.append(f"{name:<18}{count:>8}{governments[name]:>13}")
    settled = sum(counts[v] for v in SETTLED)
    lines += ["", f"settled: {settled}. For a person to read: {len(bodies) - settled}."]
    if listing:
        lines.append("")
        for b, name, why in sorted(verdicts, key=lambda v: (v[1], v[0].counties, v[0].government)):
            if name not in SETTLED:
                lines.append(f"{name} | {'; '.join(b.counties)} | {b.body} | {why}")
    return "\n".join(lines)


def queue_csv(bodies: list[AgendaBody], checks: Checks, today: dt.date) -> str:
    """Every row that needs a person, as a CSV to work through. Commissioners courts first."""
    import io

    rank = {"commissioners_court": 0, "county_board": 0, "city_council": 1,
            "township_board": 1, "village_council": 1, "planning_body": 2}  # fmt: skip
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(
        ["verdict", "why", "counties", "government", "body", "kind", "platform", "agenda_page"]
    )
    rows = [(b, *verdict(b, checks, today)) for b in bodies]
    rows.sort(key=lambda r: (rank.get(r[0].body_type, 3), r[1], r[0].counties, r[0].government))
    for b, name, why in rows:
        if name not in SETTLED:
            writer.writerow(
                [name, why, "; ".join(b.counties), b.government, b.body, b.body_type, b.platform]
                + [b.agenda_url]
            )
    return out.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="What each row of the agenda inventory has earned."
    )
    parser.add_argument("--list", action="store_true", help="list every row that needs a person")
    parser.add_argument("--csv", action="store_true", help="the same list as a CSV")
    parser.add_argument("--state", choices=("TX", "MI"), default="TX")
    args = parser.parse_args(argv)
    bodies = load_inventory(state=args.state)
    checks, today = Checks(load_checks(state=args.state)), dt.date.today()
    if args.csv:
        print(queue_csv(bodies, checks, today), end="")
    else:
        print(report(bodies, checks, today, args.list))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
