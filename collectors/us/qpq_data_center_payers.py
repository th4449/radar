"""The list of payers in the QPQ Tracker's study of who paid for the data centers.

A list of companies, not of sites and not a signal. One public page holds a table of every
payer the study counts: the name the study gives it, its class, its direct giving, the number
of contributions and the states whose filings hold them. The radar keeps a copy of the page and
checks whether a company it has on record has the same name as a payer. See pipeline/study.py.

The parser reports what the table says. Nothing is guessed. If the table, its columns or a
row's shape changes, the parser stops with LayoutChanged. The run then fails and keeps the
page for a person to look at, and the list in use stays as it was. The site's API is not
called: its robots file bars /api/.

The page holds much more than the table, and its bytes change whenever the site is rebuilt.
A new copy is stored only when the table itself says something new.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from dataclasses import dataclass
from urllib.parse import urljoin

from selectolax.lexbor import LexborHTMLParser

from collectors.base import Collector, FetchResult, LayoutChanged

URL = "https://www.purchasingpolicy.org/data-centers"

_HEADERS = ("Payer", "Class", "Direct giving", "Contributions", "States")
_SUMMARY = re.compile(r"All (\d+) payers")
_PAYER_PAGE = re.compile(
    r"https://www\.purchasingpolicy\.org/entity/"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)
_DOLLARS = re.compile(r"\$(\d{1,3}(?:,\d{3})*)")
_COUNT = re.compile(r"\d{1,3}(?:,\d{3})*")
_STATE = re.compile(r"[A-Z]{2}")


@dataclass(frozen=True)
class Payer:
    name: str  # as the study writes it, such as "CMS / Consumers Energy"
    url: str  # the payer's page in the study
    payer_class: str  # the study's own word: Utility, Hyperscaler, ...
    direct_giving: int  # whole dollars
    contributions: int
    states: tuple[str, ...]


def _clean(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def parse(body: bytes) -> list[Payer]:
    """Every payer in the page's table, in page order."""
    tree = LexborHTMLParser(body.decode("utf-8", errors="replace"))
    tables = [
        t for t in tree.css("main table")
        if tuple(_clean(h.text()) for h in t.css("thead th")) == _HEADERS
    ]  # fmt: skip
    if len(tables) != 1:
        raise LayoutChanged(f"expected one table of payers, found {len(tables)}")
    table = tables[0]

    # The page says how many payers it lists. A table of another length is not the whole list.
    box = table.parent
    while box is not None and box.tag != "details":
        box = box.parent
    summary = box.css_first("summary") if box is not None else None
    said = _SUMMARY.fullmatch(_clean(summary.text())) if summary is not None else None
    if said is None:
        raise LayoutChanged("the table of payers has lost its count")

    out: list[Payer] = []
    for row in table.css("tbody tr"):
        cells = row.css("td")
        link = cells[0].css_first("a") if len(cells) == len(_HEADERS) else None
        if link is None:
            raise LayoutChanged(f"unexpected row shape: {_clean(row.text())[:80]!r}")
        name = _clean(link.text())
        url = urljoin(URL, link.attributes.get("href") or "")
        giving = _DOLLARS.fullmatch(_clean(cells[2].text()))
        count = _COUNT.fullmatch(_clean(cells[3].text()))
        states = tuple(s.strip() for s in _clean(cells[4].text()).split(","))
        payer_class = _clean(cells[1].text())
        if not (name and payer_class and giving and count and _PAYER_PAGE.fullmatch(url)):
            raise LayoutChanged(f"a payer row could not be read: {_clean(row.text())[:80]!r}")
        if not all(_STATE.fullmatch(s) for s in states):
            raise LayoutChanged(f"unexpected states for {name!r}: {cells[4].text()!r}")
        out.append(
            Payer(
                name=name,
                url=url,
                payer_class=payer_class,
                direct_giving=int(giving.group(1).replace(",", "")),
                contributions=int(count.group(0).replace(",", "")),
                states=states,
            )
        )
    if len(out) != int(said.group(1)):
        raise LayoutChanged(f"the page says {said.group(1)} payers and the table has {len(out)}")
    if len({p.url for p in out}) != len(out) or len({p.name for p in out}) != len(out):
        raise LayoutChanged("two rows of the table are the same payer")
    return out


class QpqDataCenterPayers(Collector):
    source_id = "us_qpq_data_center_payers"

    def urls(self) -> list[str]:
        return [URL]

    def content_key(self, result: FetchResult) -> str:
        """Changes only when the table of payers does. Raises LayoutChanged if it cannot be read."""
        rows = [dataclasses.asdict(p) for p in parse(result.body)]
        return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
