"""ERCOT committee meetings and the files posted for them.

ERCOT gives each committee an index page that links to one page per meeting. A meeting page has
an agenda and, once ERCOT posts them, the files for that meeting under /files/docs/. The
Regional Planning Group, the Large Load Working Group and the Technical Advisory Committee all
use this layout.

A collector walks index, then meeting pages near today, then their files. It follows no other
link. ERCOT's robots rules close its calendar feed and its committee widget, and the fetcher
would refuse them in any case.

The parsers report what a page says. A date that cannot be read is kept as text with no parsed
value. If a page stops looking like the saved copies, the parser stops with LayoutChanged.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import ClassVar
from urllib.parse import urljoin, urlsplit

from selectolax.lexbor import LexborHTMLParser, LexborNode

from collectors.base import Collector, FetchResult, LayoutChanged

HOST = "www.ercot.com"

_FILES_PREFIX = "/files/docs/"
_DATE_FORMATS = ("%b %d, %Y", "%B %d, %Y")


@dataclass(frozen=True)
class Committee:
    index: str  # the committee's index page
    name: str  # as ERCOT writes it in meeting addresses: RPG, LLWG, TAC
    files: re.Pattern[str] | None = None  # if set, only files whose title matches are fetched

    @property
    def meeting_path(self) -> re.Pattern[str]:
        # /calendar/11032026-RPG-Meeting, /calendar/05062026-Special-TAC-Meeting,
        # /calendar/06302026-TAC-Meeting-_-Webex
        return re.compile(
            rf"^/calendar/(\d{{2}})(\d{{2}})(\d{{4}})-(?:Special-)?{re.escape(self.name)}-Meeting[\w-]*$"
        )


@dataclass(frozen=True)
class MeetingLink:
    url: str
    date: dt.date | None  # from the link text
    date_text: str
    slug_date: dt.date | None  # from the address, which also carries the date


@dataclass(frozen=True)
class MeetingFile:
    url: str
    title: str
    section: str  # the heading the file is listed under
    caption: str  # as shown, for example "Nov 2, 2026 - pdf - 1.6 MB"
    posted: dt.date | None  # the date in the caption


@dataclass(frozen=True)
class Meeting:
    title: str
    date: dt.date | None
    date_text: str
    topics: tuple[str, ...]
    files: tuple[MeetingFile, ...]


def _clean(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def _date(text: str) -> dt.date | None:
    for fmt in _DATE_FORMATS:
        try:
            return dt.datetime.strptime(text, fmt).date()  # noqa: DTZ007 - a calendar date
        except ValueError:
            continue
    return None


def _on_site(href: str | None, base: str) -> tuple[str, str] | None:
    """The absolute URL and its path, if the link stays on ERCOT's public site."""
    if not href:
        return None
    url = urljoin(base, href.strip())
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.netloc != HOST:
        return None
    return url, parts.path


def parse_index(body: bytes, committee: Committee) -> list[MeetingLink]:
    """Every meeting of this committee the index page links to, once each, in page order.

    An index can also link to other committees' meetings. Those are left out.
    """
    tree = LexborHTMLParser(body.decode("utf-8", errors="replace"))
    pattern = committee.meeting_path
    seen: set[str] = set()
    out: list[MeetingLink] = []
    for a in tree.css("a"):
        found = _on_site(a.attributes.get("href"), committee.index)
        if found is None:
            continue
        url, path = found
        match = pattern.match(path)
        if not match or url in seen:
            continue
        seen.add(url)
        month, day, year = (int(g) for g in match.groups())
        try:
            slug_date = dt.date(year, month, day)
        except ValueError:
            slug_date = None
        text = _clean(a.text())
        out.append(MeetingLink(url, _date(text), text, slug_date))
    if not out:
        raise LayoutChanged("the index page links to no meetings")
    return out


def _ancestor(node: LexborNode, test) -> LexborNode | None:
    current = node.parent
    while current is not None:
        if test(current):
            return current
        current = current.parent
    return None


def _has_class(name: str):
    return lambda n: name in (n.attributes.get("class") or "").split()


def parse_meeting(body: bytes, url: str) -> Meeting:
    """The title, date, agenda topics and posted files of one meeting page."""
    tree = LexborHTMLParser(body.decode("utf-8", errors="replace"))
    details = tree.css_first("div.meeting_details")
    if details is None:
        raise LayoutChanged("no meeting details block")
    title = details.css_first("div.name h2")
    when = details.css_first("td.meeting-datetime strong")
    if title is None or when is None:
        raise LayoutChanged("no meeting title or date")
    date_text = _clean(when.text())

    topics = tuple(t for t in (_clean(c.text()) for c in details.css("div.agenda td.topic")) if t)

    files: list[MeetingFile] = []
    seen: set[str] = set()
    for a in details.css("a"):
        found = _on_site(a.attributes.get("href"), url)
        if found is None or not found[1].startswith(_FILES_PREFIX) or found[0] in seen:
            continue
        seen.add(found[0])
        row = _ancestor(a, _has_class("wrapper"))
        section = _ancestor(a, lambda n: n.attributes.get("name") == "section")
        if row is None or section is None:
            raise LayoutChanged(f"a file link outside a document list: {found[0]}")
        heading = section.css_first("div.title h2")
        caption_node = row.css_first("div.caption")
        caption = _clean(caption_node.text()) if caption_node is not None else ""
        files.append(
            MeetingFile(
                url=found[0],
                title=_clean(a.text()),
                section=_clean(heading.text()) if heading is not None else "",
                caption=caption,
                posted=_date(caption.split(" - ")[0]) if caption else None,
            )
        )
    return Meeting(_clean(title.text()), _date(date_text), date_text, topics, tuple(files))


class ErcotMeetings(Collector):
    """Index, then the meetings near today, then their files.

    A meeting's files appear in the days before it and can change shortly after, so each run
    reads the meetings from back_days ago to ahead_days from now. Older meetings are settled.
    """

    committees: ClassVar[tuple[Committee, ...]]
    back_days: ClassVar[int] = 35
    ahead_days: ClassVar[int] = 14

    def __init__(
        self,
        today: dt.date | None = None,
        back_days: int | None = None,
        ahead_days: int | None = None,
    ) -> None:
        self.today = today or dt.datetime.now(dt.UTC).date()
        if back_days is not None:
            self.back_days = back_days
        if ahead_days is not None:
            self.ahead_days = ahead_days
        self._parsed: dict[str, list[MeetingLink] | Meeting] = {}

    def urls(self) -> list[str]:
        return [committee.index for committee in self.committees]

    def _committee(self, url: str) -> tuple[Committee, bool] | None:
        """The committee a page belongs to, and whether the page is its index."""
        path = urlsplit(url).path
        for committee in self.committees:
            if url == committee.index:
                return committee, True
            if committee.meeting_path.match(path):
                return committee, False
        return None

    def _parse(self, result: FetchResult) -> list[MeetingLink] | Meeting | None:
        """Parse a page once. Files are not parsed here."""
        if result.url not in self._parsed:
            found = self._committee(result.url)
            if found is None:
                return None
            committee, is_index = found
            self._parsed[result.url] = (
                parse_index(result.body, committee)
                if is_index
                else parse_meeting(result.body, result.url)
            )
        return self._parsed[result.url]

    def content_key(self, result: FetchResult) -> str | None:
        # ERCOT's pages carry tracking codes that differ on every request. The key is taken
        # from what the page says, so an unchanged page is not stored again.
        parsed = self._parse(result)
        if parsed is None:
            return None
        return hashlib.sha256(repr(parsed).encode()).hexdigest()

    def follow(self, result: FetchResult) -> Iterable[str]:
        parsed = self._parse(result)
        if isinstance(parsed, list):
            first = self.today - dt.timedelta(days=self.back_days)
            last = self.today + dt.timedelta(days=self.ahead_days)
            dated = [(link.date or link.slug_date, link.url) for link in parsed]
            return [url for day, url in sorted(d for d in dated if d[0]) if first <= day <= last]
        if isinstance(parsed, Meeting):
            committee, _ = self._committee(result.url)
            wanted = committee.files
            return [f.url for f in parsed.files if wanted is None or wanted.search(f.title)]
        return ()
