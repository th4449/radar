"""Texas Comptroller lists of registered data centers.

Baseline layer: these are sites the state already lists, not signals of a new project. One page
holds two tables, one for qualifying data centers and one for qualifying large data center
projects. Neither table has a county or an address.

The parser reports what the page says. A date the state typed in a form we cannot read, such as
"06/172026", is kept as text and its parsed value is left empty. Nothing is guessed. If the page
layout changes, the parser stops with LayoutChanged, so a person looks before anything is stored.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

from selectolax.lexbor import LexborHTMLParser, LexborNode

from collectors.base import Collector, LayoutChanged

URL = "https://comptroller.texas.gov/taxes/data-centers/data-center-lists.php"

QUALIFYING = "qualifying_data_center"
LARGE = "qualifying_large_data_center_project"
_PROGRAMS = {
    "registered qualifying data center projects": QUALIFYING,
    "registered qualifying large data center projects": LARGE,
}
_HEADERS = (
    "Data Center",
    "Effective Date",
    "Owner Name",
    "Owner Registration Number",
    "Occupant Name",
    "Occupant Registration Number",
    "Operator Name",
    "Operator Registration Number",
    "Exemption End Date",
)
_DATE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")


@dataclass(frozen=True)
class Registration:
    program: str
    name: str
    effective_date: dt.date | None
    effective_date_text: str
    owners: tuple[str, ...]
    owner_registrations: tuple[str, ...]
    occupants: tuple[str, ...]
    occupant_registrations: tuple[str, ...]
    operators: tuple[str, ...]
    operator_registrations: tuple[str, ...]
    exemption_end_date: dt.date | None
    exemption_end_date_text: str


def _clean(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def _values(cell: LexborNode) -> tuple[str, ...]:
    """A cell holds one value, or a list when a site has several owners or operators."""
    items = cell.css("li")
    texts = [_clean(i.text()) for i in items] if items else [_clean(cell.text())]
    return tuple(t for t in texts if t)


def _date(text: str) -> dt.date | None:
    match = _DATE.fullmatch(text)
    if not match:
        return None
    month, day, year = (int(g) for g in match.groups())
    try:
        return dt.date(year, month, day)
    except ValueError:
        return None


def _program(table: LexborNode) -> str:
    parent = table.parent
    summary = parent.css_first("summary") if parent is not None else None
    label = _clean(summary.text()).lower() if summary is not None else ""
    if label not in _PROGRAMS:
        raise LayoutChanged(f"unrecognized table label: {label!r}")
    return _PROGRAMS[label]


def parse(body: bytes) -> list[Registration]:
    """Every registration on the page, in page order."""
    tree = LexborHTMLParser(body.decode("utf-8", errors="replace"))
    tables = tree.css("main table")
    if len(tables) != len(_PROGRAMS):
        raise LayoutChanged(f"expected {len(_PROGRAMS)} tables, found {len(tables)}")

    out: list[Registration] = []
    for table in tables:
        program = _program(table)
        headers = tuple(_clean(h.text()) for h in table.css("thead th"))
        if headers != _HEADERS:
            raise LayoutChanged(f"unexpected column headers: {headers}")
        for row in table.css("tbody tr"):
            name_cell = row.css_first("th")
            cells = row.css("td")
            # The state leaves the last cell off some rows. More than one missing is a new layout.
            if name_cell is None or not len(_HEADERS) - 2 <= len(cells) <= len(_HEADERS) - 1:
                raise LayoutChanged(f"unexpected row shape: {_clean(row.text())[:80]!r}")
            effective = _clean(cells[0].text())
            end = _clean(cells[7].text()) if len(cells) > 7 else ""
            out.append(
                Registration(
                    program=program,
                    name=_clean(name_cell.text()),
                    effective_date=_date(effective),
                    effective_date_text=effective,
                    owners=_values(cells[1]),
                    owner_registrations=_values(cells[2]),
                    occupants=_values(cells[3]),
                    occupant_registrations=_values(cells[4]),
                    operators=_values(cells[5]),
                    operator_registrations=_values(cells[6]),
                    exemption_end_date=_date(end),
                    exemption_end_date_text=end,
                )
            )
    return out


class ComptrollerDataCenters(Collector):
    source_id = "tx_comptroller_data_centers"

    def urls(self) -> list[str]:
        return [URL]
