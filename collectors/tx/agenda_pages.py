"""Meeting agendas that Texas governments post as files on their own websites.

Each government has one page that lists its agendas, recorded in the agenda inventory. This
collector reads that page, finds the links to agenda files and fetches the recent ones.

For each page, one run makes:

  one request for the page, then
  one request for each agenda file that is recent and not stored yet, four at most.

A file is fetched only from the government's own site or its site builder's file host. A page
that lists no agenda does not stop the run: the run log names it for a person to look at.

Some county sites keep their agendas in a calendar and not in a list. That calendar publishes
a feed of the meetings to come, made for programs, with each agenda attached to its meeting.
Where a page names such a feed, the run makes one more request, for the feed.

Every site has its own robots file and its own terms. The shared fetcher checks the robots file
of every host before every request, the file hosts included. Which governments are read is
decided by the agenda inventory: `cleared_pages` returns a page only when an independent check
confirmed it and the government's own terms were read with nothing against them. See
pipeline/agenda_checks.py and docs/sources/tx_agendas_own_sites.md.

What is stored for a page is the list of agenda links found on it, not the page. What is stored
for an agenda is the file itself.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import ClassVar
from urllib.parse import unquote, urljoin, urlsplit
from xml.etree.ElementTree import ParseError
from zoneinfo import ZoneInfo

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring as parse_xml
from selectolax.lexbor import LexborHTMLParser, LexborNode

from collectors.base import Collector, FetchResult, LayoutChanged, Reduced

# Files the pipeline can read. A .doc file is listed and not fetched.
_FILE = re.compile(r"\.(pdf|docx)$", re.IGNORECASE)
# An address that serves a file without naming its type, as some site builders write them.
_FILE_VIEW = re.compile(r"^/media/\d+$")
_AGENDA = re.compile(r"agenda", re.IGNORECASE)
_MEETINGS = re.compile(r"agenda|meeting", re.IGNORECASE)
# What a link says it is when it is not the agenda.
_NOT_AGENDA = re.compile(
    r"minutes|video|audio|recording|handout|action taken|presentation|quorum|cancel"
    r"|treasurer|financial",
    re.IGNORECASE,
)
# A packet is the agenda with its attachments, often hundreds of pages.
_PACKET = re.compile(r"packet", re.IGNORECASE)

_MONTH_NAMES = (
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
)  # fmt: skip
_MONTH = (
    r"(january|february|march|april|may|june|july|august|september|october|november|december"
    r"|jan|feb|mar|apr|jun|jul|aug|sept|sep|oct|nov|dec)"
)
_SEP = r"[\s./-]+"


def _month(word: str) -> int:
    return next(i for i, name in enumerate(_MONTH_NAMES, 1) if name.startswith(word.lower()[:3]))


# Each pattern gives (year, month, day) as written. Tried in this order on each text.
_DATES = (
    # November 17, 2026 and Nov. 17 2026 and Nov-17-26
    (
        re.compile(
            rf"(?<![a-z]){_MONTH}\.?{_SEP}(\d{{1,2}})(?:st|nd|rd|th)?,?{_SEP}(20\d\d|\d\d)(?!\d)",
            re.I,
        ),
        lambda m: (m.group(3), _month(m.group(1)), m.group(2)),
    ),
    # Nov16_2026: the day run onto the month, then the year in full
    (
        re.compile(rf"(?<![a-z]){_MONTH}(\d{{1,2}}){_SEP}(20\d\d)(?!\d)", re.I),
        lambda m: (m.group(3), _month(m.group(1)), m.group(2)),
    ),
    # 2026 November 10, as in Agenda2026November10
    (
        re.compile(rf"(?<!\d)(20\d\d)[\s./-]*{_MONTH}\.?[\s./-]*(\d{{1,2}})(?!\d)", re.I),
        lambda m: (m.group(1), _month(m.group(2)), m.group(3)),
    ),
    # Oct1326, a month and four digits. Not june2026: four digits that make a year are a year,
    # and the name gives a month with no day.
    (
        re.compile(rf"(?<![a-z]){_MONTH}(?!20[1-4]\d(?!\d))(\d\d)(\d\d)(?!\d)", re.I),
        lambda m: (m.group(3), _month(m.group(1)), m.group(2)),
    ),
    # 2026-11-17
    (re.compile(rf"(?<!\d)(20\d\d){_SEP}(\d{{1,2}}){_SEP}(\d{{1,2}})(?!\d)"), lambda m: m.groups()),
    # 11/17/2026, 11-17-26, 11.17.26
    (
        re.compile(rf"(?<!\d)(\d{{1,2}}){_SEP}(\d{{1,2}}){_SEP}(20\d\d|\d\d)(?!\d)"),
        lambda m: (m.group(3), m.group(1), m.group(2)),
    ),
)
# Digits run together, as in Agenda_11172026.pdf. Read only in a file's name.
_RUN = re.compile(r"(?<!\d)\d{5,8}(?!\d)")
_FIRST_YEAR = 2015


@dataclass(frozen=True)
class Page:
    """One government's agenda page."""

    url: str
    government: str
    counties: tuple[str, ...]
    bodies: tuple[str, ...]


@dataclass(frozen=True)
class AgendaLink:
    url: str
    text: str  # the link's own words
    date: dt.date | None  # the meeting's date as the page gives it. None if it gives none
    # Where the date was read: link_text, file_name, row, row_and_upload_folder or line.
    date_from: str | None
    # The month, as 2026-11, of a link that names a month and no day.
    month: str | None = None


def _valid(year: object, month: object, day: object, today: dt.date) -> dt.date | None:
    year, month, day = int(year), int(month), int(day)
    year += 2000 if year < 100 else 0
    try:
        found = dt.date(year, month, day)
    except ValueError:
        return None
    # A date far from today is a street number or a file id, not a meeting.
    if dt.date(_FIRST_YEAR, 1, 1) <= found <= today + dt.timedelta(days=180):
        return found
    return None


def _run_date(digits: str, today: dt.date) -> dt.date | None:
    """The date in a run of digits, when the run can be read as a date in one way only.

    11172026, 20261117, 111726, 261117, 8272026 and 72326 each have one reading. 1122026 has
    two, January 12 and November 2, so it has none here.
    """
    found: set[dt.date | None] = set()
    for year_len in (4, 2):
        if len(digits) <= year_len + 1:
            continue
        # The year last: month then day, each of one or two digits.
        rest, year = digits[:-year_len], digits[-year_len:]
        if year_len == 2 or year.startswith("20"):
            for cut in (1, 2):
                month, day = rest[:cut], rest[cut:]
                if 1 <= len(day) <= 2:
                    found.add(_valid(year, month, day, today))
        # The year first: then two digits each for the month and the day.
        year, rest = digits[:year_len], digits[year_len:]
        if len(rest) == 4 and (year_len == 2 or year.startswith("20")):
            found.add(_valid(year, rest[:2], rest[2:], today))
    found.discard(None)
    return found.pop() if len(found) == 1 else None


def dates_in(text: str, today: dt.date) -> list[dt.date]:
    """Every date written out in the text, each once, the surest way of writing first."""
    text = text.replace("_", " ")
    found: list[dt.date] = []
    for pattern, parts in _DATES:
        for match in pattern.finditer(text):
            day = _valid(*parts(match), today)
            if day and day not in found:
                found.append(day)
    return found


def find_date(text: str, today: dt.date, runs: bool = False) -> dt.date | None:
    """The first date written in the text. None if there is none, or none that is sure."""
    written = dates_in(text, today)
    if written:
        return written[0]
    text = text.replace("_", " ")
    if runs:
        for match in _RUN.finditer(text):
            found = _run_date(match.group(0), today)
            if found:
                return found
    return None


# A month and a year with no day: "November 2026 Agenda", "sept_2026_agenda", "june2026agenda",
# "2026-November".
_MONTH_YEAR = (
    (re.compile(rf"(?<![a-z]){_MONTH}\.?,?[\s./_-]*(20\d\d)(?!\d)", re.I), (2, 1)),
    (re.compile(rf"(?<!\d)(20\d\d)[\s./_-]+{_MONTH}(?![a-z])", re.I), (1, 2)),
)


def find_month(text: str, today: dt.date) -> str | None:
    """The month a text names when it names no day, as 2026-11. None if it names none."""
    for pattern, (year_at, month_at) in _MONTH_YEAR:
        found = pattern.search(text)
        if found and _valid(found.group(year_at), _month(found.group(month_at)), 1, today):
            return f"{int(found.group(year_at)):04d}-{_month(found.group(month_at)):02d}"
    return None


# A date with no year, as a table of one year's meetings writes it: "January 28".
_MONTH_DAY = re.compile(rf"(?<![a-z]){_MONTH}\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?!\d)", re.I)
# The folder a site builder files an upload in: /uploads/2026/01/.
_UPLOADED = re.compile(r"/(20\d\d)/(\d\d)/")
# Words a link uses when it says nothing of what it leads to.
_SAYS_NOTHING = re.compile(
    rf"\b({_MONTH[1:-1]}|view|download|open|click|here|pdf|file|link|document|the|for|of)\b|[\W\d_]",
    re.I,
)
_SCANNER_NAME = re.compile(r"^(doc|document|skm|scan|img|image)[\d_ -]", re.I)


def _address(base: str, href: str) -> str:
    """A link's full address, as it is asked for. A space in a file's name is written %20."""
    return urljoin(base, href).split("#")[0].replace(" ", "%20")


def _words(node: LexborNode | None) -> str:
    return " ".join(node.text(separator=" ").split()) if node is not None else ""


def _link_words(a: LexborNode) -> str:
    """What a link says: its text, or the label of the picture it is drawn as."""
    said = [_words(a), a.attributes.get("aria-label") or "", a.attributes.get("title") or ""]
    said += [img.attributes.get("alt") or "" for img in a.css("img")]
    return " ".join(" ".join(word for word in said if word).split())


def _up(node: LexborNode, tags: tuple[str, ...], limit: int = 8) -> LexborNode | None:
    for _ in range(limit):
        node = node.parent
        if node is None:
            return None
        if node.tag in tags:
            return node
    return None


_INLINE = ("span", "strong", "b", "em", "i", "u", "font")


def _line_before(a: LexborNode) -> str:
    """The words on a link's own line, before it: back to the last line break or block.

    A list typed as one paragraph puts each meeting on a line: "September 9, 2026 - Agenda".
    """
    said: list[str] = []
    node: LexborNode | None = a
    while node is not None:
        before = node.prev
        while before is not None and before.tag in ("-text", *_INLINE):
            said.append(before.text())
            before = before.prev
        if before is not None or node.parent is None or node.parent.tag not in _INLINE:
            break
        node = node.parent
    return " ".join(" ".join(reversed(said)).split())[-200:]


def _column(a: LexborNode) -> str:
    """The heading of the table column a link sits in. Empty when there is none."""
    cell = _up(a, ("td",))
    row = _up(cell, ("tr",), 2) if cell is not None else None
    table = _up(row, ("table",), 3) if row is not None else None
    if table is None:
        return ""
    at = [c for c in row.iter() if c.tag in ("td", "th")].index(cell)
    heads = table.css("thead th") or table.css("tr:first-child th")
    return _words(heads[at]) if at < len(heads) else ""


def _in_chrome(a: LexborNode) -> bool:
    """True for a link in the site's menu or footer, which is not part of the page's list."""
    return _up(a, ("nav", "footer"), 40) is not None


_ROW_FILES = 4  # an agenda, a packet, the minutes and a recording


def _file_links(node: LexborNode) -> list[str]:
    hrefs = [(a.attributes.get("href") or "").split("#")[0].split("?")[0] for a in node.css("a")]
    return [h for h in hrefs if _FILE.search(h) or _FILE_VIEW.search(urlsplit(h).path)]


def _month_day_in_folder(row: str, url: str, today: dt.date) -> dt.date | None:
    """The date of a row that gives a month and a day, with the year of the upload folder.

    An agenda is uploaded near its meeting. The year is taken only when the folder's month is
    within two months of the row's, so December's agenda filed in January still reads right.
    """
    said, filed = _MONTH_DAY.search(row), _UPLOADED.search(urlsplit(url).path)
    if not said or not filed:
        return None
    month, day = _month(said.group(1)), int(said.group(2))
    year, folder_month = int(filed.group(1)), int(filed.group(2))
    if not 1 <= folder_month <= 12:
        return None
    for candidate in (year, year - 1, year + 1):
        found = _valid(candidate, month, day, today)
        if found and abs((found - dt.date(year, folder_month, 15)).days) <= 75:
            return found
    return None


@dataclass(frozen=True)
class _Candidate:
    link: AgendaLink
    packet: bool


def find_agenda_links(body: bytes, page_url: str, today: dt.date) -> list[AgendaLink]:
    """Links to agenda files on a page, in the order the page gives them, each once.

    A link is taken when it leads to a file and says it is an agenda: in its own words, in its
    file's name, in the heading of its table column, or in its row when the link itself says
    nothing. On a page whose own title or address speaks of agendas or meetings, a file with a
    date is taken too. A link that says it is the minutes or a recording is left. So is a
    packet, when the page has the plain agenda for the same day.
    """
    tree = LexborHTMLParser(body)
    title = _words(tree.css_first("title"))
    about_meetings = bool(_MEETINGS.search(title + " " + unquote(urlsplit(page_url).path)))
    found: list[_Candidate] = []
    seen: set[str] = set()
    for a in tree.css("a[href]"):
        href = (a.attributes.get("href") or "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        url = _address(page_url, href)
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or url in seen or _in_chrome(a):
            continue
        if not (_FILE.search(parts.path) or _FILE_VIEW.search(parts.path)):
            continue
        text = _link_words(a)
        name = unquote(parts.path.rsplit("/", 1)[-1])
        own = f"{text} {name}"
        column = _column(a)
        if _NOT_AGENDA.search(own) or _NOT_AGENDA.search(column):
            continue
        held = _up(a, ("tr", "li", "article", "p"), 6)
        row = _words(held)[:400]
        # The page's words about this link come first. Then the file's name, which can be the
        # day the file was written or posted. A row is read only when it is about one meeting:
        # it holds one date and a few files. A scanner's file name is never read.
        named = None if _SCANNER_NAME.match(name) else name
        day, date_from = find_date(text, today), "link_text"
        if day is None and named:
            day, date_from = find_date(named, today), "file_name"
        if day is None and held is not None and len(_file_links(held)) <= _ROW_FILES:
            written = dates_in(row, today)
            if len(written) == 1:
                day, date_from = written[0], "row"
            elif not written and len(set(_MONTH_DAY.findall(row))) == 1:
                day, date_from = _month_day_in_folder(row, url, today), "row_and_upload_folder"
        if day is None:
            written = dates_in(_line_before(a), today)
            if len(written) == 1:
                day, date_from = written[0], "line"
        if day is None and named:
            day, date_from = find_date(named, today, runs=True), "file_name"
        month = None
        if day is None:
            date_from = None
            month = find_month(text, today) or (find_month(named, today) if named else None)
        silent = not _SAYS_NOTHING.sub("", text)
        says_agenda = bool(
            _AGENDA.search(own)
            or _AGENDA.search(column)
            or (silent and _AGENDA.search(row) and len(row) < 200)
        )
        # A month alone is not enough: a report for October is named for its month too.
        if not (says_agenda or (about_meetings and day)):
            continue
        seen.add(url)
        link = AgendaLink(url, text[:160], day, date_from, month)
        found.append(_Candidate(link, bool(_PACKET.search(own))))
    plain = {c.link.date for c in found if not c.packet}
    return [c.link for c in found if not (c.packet and (c.link.date in plain or not c.link.date))]


# The calendar on the sites the Texas Association of Counties provides. It publishes a feed of
# the meetings to come, and a county attaches each agenda to its meeting there. The feed and
# the files sit on the association's own host.
CALENDAR_HOST = "newtools.cira.state.tx.us"
_FEED = re.compile(r"https://newtools\.cira\.state\.tx\.us/page/calrss/\d+/\d+/calendar\.rss")
# The feed gives each meeting's start in Greenwich time. A 6 p.m. meeting in Texas is the next
# day there. All but two Texas counties keep Central time, and those two are an hour behind.
_TEXAS = ZoneInfo("America/Chicago")


def find_calendar_feed(body: bytes) -> str | None:
    """The address of the calendar feed a page names, if it names one."""
    found = _FEED.search(body.decode("utf-8", "replace"))
    return found.group(0) if found else None


def _meeting_day(when: str | None) -> dt.date | None:
    try:
        start = parsedate_to_datetime(when or "")
    except (TypeError, ValueError):
        return None
    if start.tzinfo is None:
        return None  # a time with no zone could be either day
    return start.astimezone(_TEXAS).date()


def find_feed_links(body: bytes, feed_url: str) -> list[AgendaLink]:
    """Agenda files attached to the meetings in a calendar feed, in its order, each once.

    A link is taken when it leads to a file and its own words or its file's name say it is an
    agenda. Its date is the day its meeting starts, in Texas time. A packet is left when the
    meeting has the plain agenda too.
    """
    try:
        root = parse_xml(body)
    except (ParseError, DefusedXmlException) as exc:
        raise LayoutChanged("the calendar feed could not be read as a feed") from exc
    if root.tag != "rss" or root.find("channel") is None:
        raise LayoutChanged("the calendar feed is not the feed it was")
    found: list[_Candidate] = []
    seen: set[str] = set()
    for item in root.iter("item"):
        day = _meeting_day(item.findtext("pubDate"))
        for a in LexborHTMLParser(item.findtext("description") or "").css("a[href]"):
            url = _address(feed_url, (a.attributes.get("href") or "").strip())
            parts = urlsplit(url)
            if parts.scheme not in ("http", "https") or url in seen:
                continue
            if not _FILE.search(parts.path):
                continue
            text = _link_words(a)
            own = f"{text} {unquote(parts.path.rsplit('/', 1)[-1])}"
            if not _AGENDA.search(own) or _NOT_AGENDA.search(own):
                continue
            seen.add(url)
            link = AgendaLink(url, text[:160], day, "calendar_feed" if day else None)
            found.append(_Candidate(link, bool(_PACKET.search(own))))
    plain = {c.link.date for c in found if not c.packet}
    return [c.link for c in found if not (c.packet and (c.link.date in plain or not c.link.date))]


# Where site builders keep the files of the sites they host. Each has its own robots file,
# which the fetcher reads like any other.
FILE_HOSTS = frozenset({"img1.wsimg.com", CALENDAR_HOST})


def _site(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.")


def on_the_site(link: str, page_url: str) -> bool:
    """True for a file on the government's own site or on its site builder's file host.

    The terms that were read are the government's. A link that leads anywhere else is listed
    and not followed.
    """
    return _site(link) == _site(page_url) or urlsplit(link).netloc.lower() in FILE_HOSTS


def cleared_pages(today: dt.date | None = None) -> list[Page]:
    """The agenda pages this collector may read today, from the agenda inventory."""
    from pipeline import agenda_checks, agenda_inventory

    today = today or dt.datetime.now(dt.UTC).date()
    checks = agenda_checks.Checks(agenda_checks.load_checks())
    pages: dict[str, Page] = {}
    for body in agenda_inventory.load_inventory():
        if body.platform not in ("own_site_files", "cira_county_site"):
            continue
        if not agenda_checks.collectable(body, checks, today):
            continue
        known = pages.get(body.agenda_url)
        bodies = (*known.bodies, body.body) if known else (body.body,)
        pages[body.agenda_url] = Page(body.agenda_url, body.government, body.counties, bodies)
    return [pages[url] for url in sorted(pages)]


class AgendaPages(Collector):
    """Each cleared government's agenda page, then its recent agenda files.

    A page that names a calendar feed has that feed read too.
    """

    source_id = "tx_agendas_own_sites"
    refusal_closes_host_only = True
    back_days: ClassVar[int] = 21
    ahead_days: ClassVar[int] = 60
    # A page can list years of agendas. A run takes the recent ones, a few at a time.
    max_files_per_page: ClassVar[int] = 4
    max_undated_per_page: ClassVar[int] = 2
    max_urls: ClassVar[int] = 800

    def __init__(self, pages: Iterable[Page] | None = None, today: dt.date | None = None) -> None:
        self.today = today or dt.datetime.now(dt.UTC).date()
        self.pages = {p.url: p for p in (cleared_pages(self.today) if pages is None else pages)}
        self._known: dict[str, dict] = {}
        self._links: dict[str, list[AgendaLink]] = {}
        self._feeds: dict[str, Page] = {}  # a calendar feed -> the page that named it
        self._files: dict[str, tuple[Page, AgendaLink]] = {}
        self._elsewhere: dict[str, list[str]] = {}

    def urls(self) -> list[str]:
        return list(self.pages)

    def _page_links(self, result: FetchResult) -> list[AgendaLink]:
        if result.url not in self._links:
            if result.url in self._feeds:
                found = find_feed_links(result.body, result.final_url)
            else:
                found = find_agenda_links(result.body, result.final_url, self.today)
            self._links[result.url] = found
        return self._links[result.url]

    def follow(self, result: FetchResult) -> Iterable[str]:
        listed = self.pages.get(result.url)
        page = listed or self._feeds.get(result.url)
        if page is None:
            return ()
        links = self._page_links(result)
        first = self.today - dt.timedelta(days=self.back_days)
        last = self.today + dt.timedelta(days=self.ahead_days)
        dated = sorted(
            (link for link in links if link.date and first <= link.date <= last),
            key=lambda link: link.date,
            reverse=True,
        )[: self.max_files_per_page]
        # A link that names a month and no day: last month's, this month's and those to come.
        oldest = (self.today - dt.timedelta(days=31)).strftime("%Y-%m")
        newest = last.strftime("%Y-%m")
        by_month = sorted(
            (link for link in links if link.month and oldest <= link.month <= newest),
            key=lambda link: link.month,
            reverse=True,
        )[: self.max_undated_per_page]
        # A page that dates nothing: its first links are its newest, by the usual layout.
        undated = [link for link in links if link.date is None][: self.max_undated_per_page]
        told = any(link.date or link.month for link in links)
        wanted = dated + by_month if told else undated
        out = []
        feed = find_calendar_feed(result.body) if listed else None
        if feed and feed not in self._feeds:
            self._feeds[feed] = page
            out.append(feed)
        for link in wanted:
            if not (on_the_site(link.url, result.final_url) or on_the_site(link.url, page.url)):
                self._elsewhere.setdefault(page.url, []).append(link.url)
                continue
            stored = self._known.get(link.url)
            # A stored file is asked for again only when the site gave a way to ask whether it
            # changed. Then an unchanged file costs one short answer.
            if stored is not None and not (stored.get("etag") or stored.get("last_modified")):
                continue
            self._files[link.url] = (page, link)
            out.append(link.url)
        return out

    def reduce(self, result: FetchResult) -> Reduced | None:
        page = self.pages.get(result.url) or self._feeds.get(result.url)
        if page is None:
            if result.url not in self._files:
                raise LayoutChanged(f"an address this collector did not ask for: {result.url}")
            return None  # an agenda file is stored as it is
        links = self._page_links(result)
        listing = {
            "government": page.government,
            "page": page.url,
            **({"calendar_feed": result.url} if result.url in self._feeds else {}),
            "agendas": [
                {
                    "url": link.url,
                    "text": link.text,
                    "date": link.date.isoformat() if link.date else None,
                    "date_from": link.date_from,
                    **({"month": link.month} if link.month else {}),
                }
                for link in links
            ],
        }
        body = json.dumps(listing, ensure_ascii=False, sort_keys=True, indent=1).encode()
        meta = {"record": "agenda_page", "government": page.government, "agendas": len(links)}
        return Reduced(body, "application/json", meta)

    def content_key(self, result: FetchResult) -> str | None:
        if result.url in self.pages or result.url in self._feeds:
            # The list of agenda links. The rest of a page changes without meaning anything.
            return hashlib.sha256(self.reduce(result).body).hexdigest()
        return None

    def facts(self, result: FetchResult) -> dict | None:
        page, link = self._files[result.url]
        return {
            "record": "agenda_file",
            "government": page.government,
            "counties": list(page.counties),
            "bodies": list(page.bodies),
            "page": page.url,
            "link_text": link.text,
            "meeting_date": link.date.isoformat() if link.date else None,
            "date_from": link.date_from,
            **({"meeting_month": link.month} if link.month else {}),
        }

    def run(self, *, source, sink, **kwargs):
        # follow() needs to know which files earlier runs stored.
        self._known = sink.known(source)
        return super().run(source=source, sink=_WithDetail(sink, self._detail), **kwargs)

    def _detail(self) -> dict:
        """What a person should look at after a run. A page that lists nothing has changed."""
        detail: dict = {"governments": len({p.government for p in self.pages.values()})}
        # A page whose agendas are in its calendar feed lists none itself. That is not a change.
        fed = {page.url for feed, page in self._feeds.items() if self._links.get(feed)}
        empty = sorted(u for u, links in self._links.items() if not links and u in self.pages)
        empty = [url for url in empty if url not in fed]
        if empty:
            detail["pages_with_no_agenda_links"] = empty
        if self._elsewhere:
            detail["agenda_links_on_other_hosts"] = self._elsewhere
        return detail


class _WithDetail:
    """A sink that adds this collector's own notes to the run log as the run is closed."""

    def __init__(self, sink, detail) -> None:
        self._sink, self._extra = sink, detail

    def finish_run(self, run_id, summary) -> None:
        summary.detail.update(self._extra())
        self._sink.finish_run(run_id, summary)

    def __getattr__(self, name: str):
        return getattr(self._sink, name)
