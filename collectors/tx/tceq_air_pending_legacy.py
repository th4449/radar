"""TCEQ's lists of pending air permit applications on its older site.

Two pages, each one table:

- New Source Review permits. From August 31, 2026 TCEQ publishes new applications of this kind
  in its Permit Search Portal, so this list holds the applications that were complete before
  that date.
- Title V operating permits. This list is still updated.

The collector reads the two pages and nothing else. Each row links to the application file, a
PDF. The collector keeps that address and does not fetch the file.

The parser reports what a page says. A date that cannot be read is kept as text with no parsed
value. If a page stops looking like the saved copies, the parser stops with LayoutChanged.

Some applicants are people, not companies. The radar does not publish the names of private
individuals, so a later step must hold those rows back.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from selectolax.lexbor import LexborHTMLParser, LexborNode

from collectors.base import Collector, FetchResult, LayoutChanged

HOST = "www.tceq.texas.gov"
_FOLDER = "/assets/public/permitting/air/reports/applications/"
NSR = f"https://{HOST}{_FOLDER}nsr-pending-permits.html"
TITLE_V = f"https://{HOST}{_FOLDER}titlev-pending-permits.html"

# The two lists name the second column differently.
_COLUMNS = (
    ("Applicant Name", "Facility Name", "Permit Number", "Received Date", "Application Link"),
    ("Applicant Name", "Area Name", "Permit Number", "Received Date", "Application Link"),
)
_UPDATED = re.compile(r"Data Updated:\s*(\d{1,2}/\d{1,2}/\d{4})")
_LETTER_SUFFIX = re.compile(r"-[A-Z#]$")


@dataclass(frozen=True)
class PendingApplication:
    applicant: str
    site: str  # the "Facility Name" or "Area Name" column
    permit_number: str
    received: dt.date | None
    received_text: str
    stage: str  # the link text, for example "Administrative Complete Application"
    application_url: str  # the application file. Kept, not fetched.
    section: str  # the heading the row sits under. Empty on the Title V list.
    notice_url: str | None  # the plain language notice, where the row links one


@dataclass(frozen=True)
class PendingList:
    title: str
    data_updated: dt.date | None
    data_updated_text: str
    rows: tuple[PendingApplication, ...]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _date(text: str) -> dt.date | None:
    try:
        return dt.datetime.strptime(text, "%m/%d/%Y").date()
    except ValueError:
        return None


def _href(a: LexborNode, base: str) -> str:
    # The pages wrap long lines, and some addresses are broken across two of them.
    return urljoin(base, re.sub(r"\s+", "", a.attributes.get("href") or ""))


def _own_text(cell: LexborNode) -> str:
    """The text of a cell up to its first line break or link."""
    parts: list[str] = []
    node = cell.child
    while node is not None and node.tag not in ("br", "a"):
        parts.append(node.text() or "")
        node = node.next
    return _clean("".join(parts))


def _section(heading_id: str) -> str:
    """'Standard Permits-B' is the B block of 'Standard Permits'. 'B' alone has no section."""
    name = _LETTER_SUFFIX.sub("", _clean(heading_id))
    return name if len(name) > 1 else ""


def parse_list(body: bytes, url: str = NSR) -> PendingList:
    tree = LexborHTMLParser(body)
    title = tree.css_first("#header h2")
    if title is None:
        raise LayoutChanged("no list title")
    header = tree.css_first("#header")
    updated = _UPDATED.search(_clean(header.text())) if header is not None else None
    if updated is None:
        raise LayoutChanged("no 'Data Updated' date")

    table = None
    for candidate in tree.css("table.report"):
        columns = tuple(_clean(th.text()) for th in candidate.css("th"))
        if columns in _COLUMNS:
            table = candidate
            break
    if table is None:
        raise LayoutChanged("no table with the expected five columns")

    rows: list[PendingApplication] = []
    section = ""
    for tr in table.css("tr"):
        cells = tr.css("td")
        if not cells:
            continue  # the column headings
        if len(cells) != 5:
            raise LayoutChanged(f"a row has {len(cells)} cells, not 5")
        heading_id = cells[0].attributes.get("id")
        if heading_id:
            section = _section(heading_id)
            continue
        applicant = _own_text(cells[0])
        files = [
            (_href(a, url), _clean(a.text()))
            for a in cells[4].css("a[href]")
            if urlsplit(_href(a, url)).path.startswith(_FOLDER)
            and urlsplit(_href(a, url)).netloc == HOST
        ]
        if not applicant or len(files) != 1:
            raise LayoutChanged(f"row {len(rows) + 1} has no applicant or no single application")
        notices = [_href(a, url) for a in cells[0].css("a[href]") if "#" in _href(a, url)]
        received_text = _clean(cells[3].text())
        rows.append(
            PendingApplication(
                applicant=applicant,
                site=_clean(cells[1].text()),
                permit_number=_clean(cells[2].text()),
                received=_date(received_text),
                received_text=received_text,
                stage=files[0][1],
                application_url=files[0][0],
                section=section,
                notice_url=notices[0] if notices else None,
            )
        )
    if not rows:
        raise LayoutChanged("the table lists no applications")
    return PendingList(_clean(title.text()), _date(updated.group(1)), updated.group(1), tuple(rows))


class TceqAirPendingLegacy(Collector):
    """The two list pages, and nothing they link to."""

    source_id = "tx_tceq_air_pending_legacy"

    def urls(self) -> list[str]:
        return [NSR, TITLE_V]

    def content_key(self, result: FetchResult) -> str | None:
        # The New Source Review page is rebuilt every day with a new "Report Run" date even
        # when its data has not changed. The key is taken from the rows and the "Data Updated"
        # date, so an unchanged list is not stored again.
        parsed = parse_list(result.body, result.url)
        return hashlib.sha256(repr(parsed).encode()).hexdigest()
