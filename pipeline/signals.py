"""Turn one stored document into draft signals. See BUILD_PLAN.md milestone M4.

A signal is one dated fact from one document. The rules here are deliberately narrow.

- **A record needs a stated reason.** A pending air permit or a well report means nothing by
  itself. A row becomes a signal only when it says "data center", uses a code word, or names a
  company on the Comptroller's registered data center list. The reason is stored with the
  signal, with the words that matched.
- **A record that may name a person makes no signal.** The named party must show a company or
  a public body. Otherwise the record is counted as held back, by its number and never by
  its name.
- **A summary restates the record.** It says what the source lists. It never says a data
  center is planned.
- **Nothing is guessed.** No date, no signal. A county comes only from the record.

Nothing in this module touches the database or the network.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import posixpath
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from urllib.parse import unquote, urlsplit

from collectors.base import LayoutChanged
from collectors.tx import comptroller_data_centers, tceq_air_pending_legacy, twdb_well_reports
from collectors.tx.agenda_pages import find_date
from pipeline.classify import Hit, KeywordRules, snippet
from pipeline.config import load_entities, load_scoring
from pipeline.counties import CountyIndex
from pipeline.entities import Party, canonical_name, classify_party, find_companies, match_key
from pipeline.quantities import find_quantities

# Bump this when a rule in this module changes, so stored documents are read again.
RULES_VERSION = "2026-11-23.2"

LISTING_SOURCE = "tx_comptroller_data_centers"
MAX_EVIDENCE = 20  # snippets or quantities kept with one signal
_NARROW = 40  # margin around a match in free text that a person may have typed

# Texas, with a margin. A well report's coordinates are typed by the driller.
_TX_BOX = (-107.0, 25.5, -93.0, 37.0)


# --- what a processor is given and gives back ---------------------------------------------------


@dataclass(frozen=True)
class Doc:
    """A stored document, as a processor sees it."""

    source_id: str
    url: str
    retrieved_at: dt.datetime
    sha256: str
    text: str
    meta: dict
    body: bytes  # the stored file


@dataclass(frozen=True)
class Draft:
    signal_type: str
    key: str  # what makes this fact itself within its source, such as a report number
    event_date: dt.date
    summary: str
    confidence: float
    county_fips: str | None
    party: str | None  # the company or public body the record names, as written
    party_kind: str | None  # company or public_body
    extracted: dict

    def fingerprint(self, source_id: str) -> str:
        """The same fact gives the same value, whichever copy of a list it was read from."""
        text = f"{source_id}\n{self.signal_type}\n{self.key}"
        return hashlib.sha256(text.encode()).hexdigest()


@dataclass
class Outcome:
    drafts: list[Draft] = field(default_factory=list)
    records: int = 0  # rows or files looked at
    no_reason: int = 0  # nothing in the record gives a reason
    held_back: int = 0  # a reason, but the named party may be a person
    held_refs: list[str] = field(default_factory=list)  # record numbers, never names
    out_of_scope: int = 0  # the record is in a county outside the test set
    undated: int = 0  # a reason, but no date that can be read
    no_text: int = 0  # a file with no text in it, such as a scan. Nobody has read it
    own_computers: int = 0  # "data center" used of a government's own computers. Set aside
    county_fips: str | None = None  # set when the whole document is about one county

    def counts(self) -> dict[str, int]:
        counts = {
            "records": self.records,
            "signals": len(self.drafts),
            "no_reason": self.no_reason,
            "held_back": self.held_back,
            "out_of_scope": self.out_of_scope,
            "undated": self.undated,
        }
        if self.no_text:
            counts["no_text"] = self.no_text
        if self.own_computers:
            counts["own_computers"] = self.own_computers
        return counts


# --- the rules a processor works with -----------------------------------------------------------


@dataclass(frozen=True)
class Listing:
    """One appearance of a company on the Comptroller's registered data center list."""

    name: str  # as the list writes it
    role: str  # owner, occupant or operator
    data_center: str
    program: str


def read_listings(body: bytes) -> dict[str, list[Listing]]:
    """Every company on the Comptroller's list, by canonical name."""
    out: dict[str, list[Listing]] = {}
    for reg in comptroller_data_centers.parse(body):
        for role, names in (
            ("owner", reg.owners),
            ("occupant", reg.occupants),
            ("operator", reg.operators),
        ):
            for name in names:
                listing = Listing(name, role, reg.name, reg.program)
                out.setdefault(canonical_name(name), []).append(listing)
    return out


class Rules:
    """Everything the processors consult: keywords, counties, known names and the list."""

    def __init__(
        self,
        *,
        listings: dict[str, list[Listing]] | None = None,
        listings_sha256: str | None = None,
        keywords: KeywordRules | None = None,
        known_organizations: Iterable[str] | None = None,
        confidence: dict[str, float] | None = None,
    ) -> None:
        self.keywords = keywords or KeywordRules()
        self.counties = {"TX": CountyIndex.for_state("TX"), "MI": CountyIndex.for_state("MI")}
        entities = load_entities()
        names = (
            known_organizations if known_organizations is not None else entities.known_organizations
        )
        self.known = frozenset(canonical_name(n) for n in names)
        self._ordinary = frozenset(w.upper() for w in entities.ordinary_words_on_the_list)
        self.confidence = dict(confidence or load_scoring().confidence)
        self.signal_types = frozenset(load_scoring().signal_types)
        self.listings = listings or {}
        self.listings_sha256 = listings_sha256
        self._loose: dict[str, list[Listing]] = {}
        for name, found in self.listings.items():
            self._loose.setdefault(match_key(name), []).extend(found)

    def party(self, name: str) -> Party:
        return classify_party(name, self.known)

    def reasons(self, fields: dict[str, str], party: str | None) -> list[dict]:
        """Why a record is worth a signal. An empty list means it is not."""
        out: list[dict] = []
        for name, value in fields.items():
            for hit in self.keywords.find(value or ""):
                reason = {"rule": hit.kind, "term": hit.term, "field": name, "text": hit.text}
                if reason not in out:
                    out.append(reason)
        listed = self._listed(party) if party else None
        if listed:
            rule, match, found = listed
            out.append(
                {
                    "rule": rule,
                    "match": match,
                    "list": LISTING_SOURCE,
                    "list_sha256": self.listings_sha256,
                    "listed_as": [
                        {"name": x.name, "role": x.role, "data_center": x.data_center}
                        for x in found[:5]
                    ],
                }
            )
        return self.enough(out)

    def enough(self, reasons: list[dict]) -> list[dict]:
        """The reasons, or none when the only one is a term that is no reason by itself.

        See `only_with_another_term` in config/keywords.yaml. A company on the Comptroller's
        list, or a reason a person stated, is a reason of its own.
        """
        terms = [r["term"] for r in reasons if "term" in r]
        if len(terms) == len(reasons) and not self.keywords.stands_alone(terms):
            return []
        return reasons

    def _listed(self, party: str) -> tuple[str, str, list[Listing]] | None:
        """How a name relates to the Comptroller's list, from the closest match down."""
        exact = self.listings.get(canonical_name(party))
        if exact:
            return "listed_company", "the same name", exact
        key = match_key(party)
        if key in self._loose:
            return "listed_company_loose", "the same name with another legal form", self._loose[key]
        # A project company is often named for its parent and a place: "Example Bosque LLC".
        words = key.split()
        for n in range(len(words) - 1, 0, -1):
            start = " ".join(words[:n])
            if start in self._loose and not (n == 1 and start in self._ordinary):
                return (
                    "listed_company_loose",
                    "the name starts with a listed name",
                    self._loose[start],
                )
        return None

    def listings_for(self, party: str) -> list[Listing]:
        """Every appearance on the Comptroller's list that the rules tie to this name."""
        listed = self._listed(party)
        return listed[2] if listed else []

    def how_sure(self, reasons: list[dict]) -> float:
        return max(self.confidence[r["rule"]] for r in reasons)


# --- small helpers ------------------------------------------------------------------------------


def _long_date(day: dt.date) -> str:
    return f"{day:%B} {day.day}, {day.year}"


def _iso_date(text: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(text.strip()[:10])
    except ValueError:
        return None


def _narrow_snippets(text: str, hits: list[Hit]) -> list[str]:
    seen: list[str] = []
    for hit in hits:
        piece = snippet(text, hit.start, hit.end, margin=_NARROW)
        if piece not in seen:
            seen.append(piece)
    return seen[:MAX_EVIDENCE]


# --- TCEQ pending air permit lists --------------------------------------------------------------

_TCEQ_KINDS = {
    tceq_air_pending_legacy.NSR: ("nsr", "New Source Review"),
    tceq_air_pending_legacy.TITLE_V: ("titlev", "Title V"),
}


_TCEQ_FOLDER = tceq_air_pending_legacy.NSR.rsplit("/", 1)[0] + "/"


def tceq_air_pending(doc: Doc, rules: Rules) -> Outcome:
    """One signal for each listed application that gives a reason and names a company."""
    if doc.url not in _TCEQ_KINDS:
        if doc.url.startswith(_TCEQ_FOLDER) and doc.url.lower().endswith(".pdf"):
            # An application file a row links. It makes no signal of its own. It is read for
            # the county of the row's signal. See pipeline/tceq_applications.py.
            return Outcome()
        raise LayoutChanged(f"not one of the two TCEQ lists: {doc.url}")
    slug, kind = _TCEQ_KINDS[doc.url]
    parsed = tceq_air_pending_legacy.parse_list(doc.body, doc.url)
    out = Outcome()
    for row in parsed.rows:
        out.records += 1
        reasons = rules.reasons({"applicant": row.applicant, "site": row.site}, row.applicant)
        if not reasons:
            out.no_reason += 1
            continue
        party = rules.party(row.applicant)
        if not party.usable:
            out.held_back += 1
            out.held_refs.append(f"TCEQ {kind} permit {row.permit_number}")
            continue
        if row.received is None:
            out.undated += 1
            continue
        out.drafts.append(
            Draft(
                signal_type="air_permit",
                key=f"{slug}:{row.permit_number}:{row.received.isoformat()}",
                event_date=row.received,
                summary=(
                    f"TCEQ lists a pending {kind} air permit application from {row.applicant} "
                    f"for {row.site or 'a site it does not name'}: permit {row.permit_number}, "
                    f"received {_long_date(row.received)}."
                ),
                confidence=rules.how_sure(reasons),
                county_fips=None,  # the lists give no county
                party=row.applicant,
                party_kind=party.kind,
                extracted={
                    "reasons": reasons,
                    "reference": f"TCEQ {kind} permit {row.permit_number}",
                    "party_basis": party.basis,
                    "list": parsed.title,
                    "list_data_updated": parsed.data_updated_text,
                    "row": {
                        "applicant": row.applicant,
                        "site": row.site,
                        "permit_number": row.permit_number,
                        "received": row.received_text,
                        "stage": row.stage,
                        "section": row.section,
                        "application_url": row.application_url,
                        "notice_url": row.notice_url,
                    },
                },
            )
        )
    return out


# --- TWDB well reports --------------------------------------------------------------------------

# Free text a driller typed. It can name a person even when the owner is a company, so it is
# searched for terms and never copied whole into a signal.
_TWDB_FREE_TEXT = ("WellLocationDescription", "Comments")


def _point(row: dict[str, str]) -> dict | None:
    try:
        lat, lon = float(row["CoordDDLat"]), float(row["CoordDDLong"])
    except ValueError:
        return None
    west, south, east, north = _TX_BOX
    if not (west <= lon <= east and south <= lat <= north):
        return None
    return {"lon": lon, "lat": lat, "from": "the well report. Not verified by state staff."}


def twdb_well_reports_extract(doc: Doc, rules: Rules) -> Outcome:
    """One signal for each kept report that gives a reason and names a company."""
    lines = doc.body.decode("utf-8").split("\n")
    columns = twdb_well_reports.KEEP
    if tuple(lines[0].split("|")) != columns:
        raise LayoutChanged("the stored extract does not have the expected columns")
    counties = rules.counties["TX"]
    out = Outcome()
    for line in lines[1:]:
        if not line:
            continue
        cells = line.split("|")
        if len(cells) != len(columns):
            raise LayoutChanged("a row of the stored extract has the wrong number of fields")
        row = dict(zip(columns, cells, strict=True))
        out.records += 1
        number, owner = row["WellReportTrackingNumber"], row["OwnerName"]
        fields = {
            "owner": owner,
            "well address": " ".join(x for x in (row["WellAddress1"], row["WellAddress2"]) if x),
            "other use": row["ProposedUseOtherDesc"],
            "location description": row["WellLocationDescription"],
            "comments": row["Comments"],
        }
        reasons = rules.reasons(fields, owner)
        if not reasons:
            out.no_reason += 1
            continue
        fips = counties.fips(row["County"])
        if fips is None:
            out.out_of_scope += 1
            continue
        party = rules.party(owner)
        if not party.usable:
            out.held_back += 1
            out.held_refs.append(f"TWDB well report {number}")
            continue
        submitted = _iso_date(row["DateSubmitted"])
        if submitted is None:
            out.undated += 1
            continue
        use = row["ProposedUse"] or "unstated use"
        work = row["TypeOfWork"] or "type of work not stated"
        free_text = {
            name: _narrow_snippets(row[name], rules.keywords.find(row[name]))
            for name in _TWDB_FREE_TEXT
            if rules.keywords.find(row[name])
        }
        out.drafts.append(
            Draft(
                signal_type="well_report",
                key=f"well_report:{number}",
                event_date=submitted,
                summary=(
                    f"Texas well report {number} names {owner} as owner of a well in "
                    f"{row['County']} County. Proposed use: {use}. Type of work: {work}. "
                    f"Submitted {_long_date(submitted)}."
                ),
                confidence=rules.how_sure(reasons),
                county_fips=fips,
                party=owner,
                party_kind=party.kind,
                extracted={
                    "reasons": reasons,
                    "reference": f"Texas well report tracking number {number}",
                    "party_basis": party.basis,
                    "point": _point(row),
                    "free_text_matches": free_text,
                    "row": {k: v for k, v in row.items() if k not in _TWDB_FREE_TEXT},
                },
            )
        )
    return out


# --- ERCOT Regional Planning Group files --------------------------------------------------------

_FILES_PREFIX = "/files/docs/"
_POSTED = re.compile(r"^/files/docs/(\d{4})/(\d{2})/(\d{2})/")
_BLANK_LINE = re.compile(r"\n\s*\n")
# ERCOT numbers each project submitted to the planning group: 25RPG020.
_RPG_NUMBER = re.compile(r"(?<![A-Za-z0-9])\d{2}RPG\d{3}(?![A-Za-z0-9])")


def _passages(text: str) -> list[tuple[int, str]]:
    """Pages or slides, with where each starts. The extractor puts a blank line between them."""
    out, at = [], 0
    for piece in _BLANK_LINE.split(text):
        start = text.index(piece, at) if piece else at
        if piece.strip():
            out.append((start, piece))
        at = start + len(piece)
    return out


def _posted(url: str) -> dt.date | None:
    match = _POSTED.match(urlsplit(url).path)
    if not match:
        return None
    try:
        return dt.date(*(int(g) for g in match.groups()))
    except ValueError:
        return None


def _terms(rules: Rules, text: str) -> list[Hit]:
    """Keyword hits in a planning file. Every transmission project there is called "Project"
    something, so a code name is not a reason in these files."""
    hits = [h for h in rules.keywords.find(text) if h.kind != "project_code_name"]
    return hits if rules.keywords.stands_alone(h.term for h in hits) else []


def ercot_rpg_file(doc: Doc, rules: Rules) -> Outcome:
    """One signal for each test county a planning group file names next to a keyword.

    Index and meeting pages are not read here: they list the files, and the files are read
    themselves. The companies a file names are mostly utilities, so no company is attached to
    the signal. They are listed with it for the reviewer.
    """
    out = Outcome()
    path = urlsplit(doc.url).path
    if not path.startswith(_FILES_PREFIX):
        return out
    out.records = 1
    text = doc.text or ""
    if not _terms(rules, text):
        out.no_reason = 1
        return out
    posted = _posted(doc.url)
    if posted is None:
        out.undated = 1
        return out

    counties = rules.counties["TX"]
    all_mentions = counties.mentions(text)
    in_scope = {m.fips for m in all_mentions if m.in_scope}
    other = sorted({m.name for m in all_mentions if not m.in_scope})

    # The passages that hold a keyword, grouped by the test county each one names.
    by_county: dict[str | None, list[tuple[str, list[Hit]]]] = {}
    unplaced: list[tuple[str, list[Hit]]] = []
    for _, passage in _passages(text):
        hits = _terms(rules, passage)
        if not hits:
            continue
        here = {m.fips for m in counties.mentions(passage) if m.in_scope}
        for fips in here:
            by_county.setdefault(fips, []).append((passage, hits))
        if not here:
            unplaced.append((passage, hits))

    placement = "the county is named in the same passage as the term"
    if not by_county:
        if len(in_scope) == 1 and not other:
            by_county = {next(iter(in_scope)): unplaced}
            placement = "the only county the file names"
        elif not all_mentions or in_scope:
            by_county = {None: unplaced}
            placement = "no single county could be tied to the term"
        else:
            out.out_of_scope = 1
            return out
    if len(in_scope) == 1 and not other:
        out.county_fips = next(iter(in_scope))

    name = unquote(posixpath.basename(path))
    for fips, found in sorted(by_county.items(), key=lambda kv: kv[0] or ""):
        hits = [h for _, passage_hits in found for h in passage_hits]
        reasons: list[dict] = []
        for hit in hits:
            reason = {"rule": hit.kind, "term": hit.term, "field": "text"}
            if reason not in reasons:
                reasons.append(reason)
        snippets: list[str] = []
        quantities: list[dict] = []
        companies: list[str] = []
        numbers: list[str] = []
        for passage, passage_hits in found:
            for number in _RPG_NUMBER.findall(passage):
                if number not in numbers:
                    numbers.append(number)
            for hit in passage_hits:
                piece = snippet(passage, hit.start, hit.end)
                if piece not in snippets:
                    snippets.append(piece)
            for q in find_quantities(passage):
                item = {
                    "kind": q.kind,
                    "value": q.value,
                    "low": q.low,
                    "text": q.text,
                    "context": snippet(passage, q.start, q.end, margin=60),
                }
                if item not in quantities:
                    quantities.append(item)
            for company in find_companies(passage):
                if company not in companies:
                    companies.append(company)
        terms = ", ".join(f'"{t}"' for t in dict.fromkeys(r["term"] for r in reasons))
        place = f" and {counties.name(fips)} County" if fips else ""
        out.drafts.append(
            Draft(
                signal_type="transmission_filing",
                key=f"{doc.url}#{fips or 'no-county'}",
                event_date=posted,
                summary=(
                    f'ERCOT Regional Planning Group file "{name}", posted {_long_date(posted)}, '
                    f"mentions {terms}{place}."
                ),
                confidence=rules.how_sure(reasons),
                county_fips=fips,
                party=None,
                party_kind=None,
                extracted={
                    "reasons": reasons,
                    "reference": f'ERCOT Regional Planning Group file "{name}"',
                    "placement": placement,
                    "snippets": snippets[:MAX_EVIDENCE],
                    "quantities": quantities[:MAX_EVIDENCE],
                    "companies_named": companies[:MAX_EVIDENCE],
                    "project_numbers": numbers[:MAX_EVIDENCE],
                    "other_counties_named": other,
                    "needs_ocr": bool(doc.meta.get("needs_ocr")),
                },
            )
        )
    return out


Processor = Callable[[Doc, Rules], Outcome]

# A source with no entry here is not read for signals. tx_ercot_large_load is context only:
# totals by zone, no sites. tx_comptroller_data_centers is the list the rules consult.
# --- meeting agendas from Legistar ---------------------------------------------------------------

_PLACE_KIND = re.compile(r"\s+(city|town|village)$")
_IN_A_COUNTY = re.compile(r"\s*\([^)]*County\)$")  # "Salem township (Washtenaw County)"
_TOWNSHIP = re.compile(r"\s+(charter\s+)?township$")


def place_name(government: str) -> str:
    """A government as people say it: "Round Rock", "Lodi Township", "Washtenaw County".

    The inventory writes a place as the Census does: "Round Rock city". The kind is dropped
    for a city, a town or a village. A Michigan township keeps it, because a township and a
    city often share a name: Ann Arbor is both.
    """
    name = _IN_A_COUNTY.sub("", government)
    township = _TOWNSHIP.search(name)
    if township:
        kind = "Charter Township" if township.group(1) else "Township"
        return f"{name[: township.start()]} {kind}"
    return _PLACE_KIND.sub("", name)


def _counties_of(doc: Doc, rules: Rules) -> CountyIndex:
    """The counties of the state a document's source belongs to: tx_... or mi_..."""
    state = doc.source_id.split("_", 1)[0].upper()
    if state not in rules.counties:
        raise ValueError(f"{doc.source_id} is a source from no state the radar reads")
    return rules.counties[state]


# An agenda calls every road job "Project" something. A code name is a reason only where the
# agenda speaks of economic development negotiations, the closed session Texas law allows for
# them under Government Code 551.087.
_NEGOTIATIONS = re.compile(r"economic\s+development|551\.087", re.IGNORECASE)


def _meeting(government: str, day: dt.date, reasons: list[dict]) -> str | None:
    """What holds an agenda record to a site: its government and meeting.

    Only for a record that says "data center". An agenda signal carries no company, so
    without this it sits on no site and no reviewer sees it. A code word alone is too weak
    to open a site. Approved by the owner on November 23, 2026, after the backtest.
    """
    if not any(r["rule"] == "direct_term" for r in reasons):
        return None
    return f"{place_name(government)}, meeting of {_long_date(day)}"


def _rule_making(words: list[str]) -> dict:
    """What is kept with a signal when "data center" sits beside the words of rule making."""
    return {"rule_making": {"words": words}} if words else {}


def _set_aside(own: str | None) -> dict:
    """What is kept with a signal when the words "data center" in its record were set aside."""
    return {"set_aside": {"rule": "own_computers", "shows": own}} if own else {}


# Where an agenda item starts: "12.", "(b)", "iv." at the head of a line.
_ITEM_START = re.compile(r"(?m)^[ \t]*(?:\(?\d{1,3}[.)]|\(?[A-Za-z][.)]|[ivxIVX]{1,4}[.)])[ \t]")
_ITEM_REACH = 700  # an item longer than this is cut to the words near the term
_NEAR = 250


def _agenda_item(passage: str, start: int, end: int) -> str:
    """The agenda item that holds a term: from the item's own start to the next item's.

    A file has no items to tell apart for certain. Where no item start is near, the words
    close to the term stand in for the item.
    """
    before = [m.start() for m in _ITEM_START.finditer(passage, max(0, start - _ITEM_REACH), start)]
    after = _ITEM_START.search(passage, end, min(len(passage), end + _ITEM_REACH))
    first = before[-1] if before else max(0, start - _NEAR)
    last = after.start() if after else min(len(passage), end + _NEAR)
    return passage[first:last]


def _body_name(government: str, body: str) -> str:
    """ "Round Rock City Council", "Harris County Commissioners Court"."""
    place = place_name(government)
    return body if body.lower().startswith(place.lower()) else f"{place} {body}"


def legistar_agenda(doc: Doc, rules: Rules) -> Outcome:
    """One signal for each agenda item that uses a term the radar looks for.

    An agenda names people: staff, appointees, applicants. So the summary never quotes an item.
    It says which body, which meeting, which item and which words. The words around the match
    are kept beside the signal for the reviewer, who opens the meeting's own page to read it.
    """
    out = Outcome()
    if doc.meta.get("record") != "legistar_agenda":
        return out  # the list of meetings holds nothing to read
    agenda = json.loads(doc.body)
    day = _iso_date(str(agenda.get("date") or ""))
    counties = _counties_of(doc, rules)
    named = [str(c) for c in agenda.get("counties") or []]
    in_scope = [f for f in (counties.fips(name) for name in named) if f]
    fips = in_scope[0] if in_scope else None
    out.county_fips = fips
    who = _body_name(str(agenda["government"]), str(agenda["body"]))
    for item in agenda["items"]:
        fields = {"title": item.get("title") or "", "note": item.get("note") or ""}
        text = " ".join(v for v in fields.values() if v)
        if not text:
            continue
        out.records += 1
        # Every public works item is a "Project" something. As in an agenda file, a code name
        # is a reason only where the item speaks of economic development negotiations.
        negotiations = bool(_NEGOTIATIONS.search(text))
        reasons = [
            r
            for r in rules.reasons(fields, None)
            if r["rule"] != "project_code_name" or negotiations
        ]
        # A county renewing its hosting contract says "data center" too. Those words are set
        # aside in an item about the government's own computers. Another term still counts.
        own = None
        if any(r["rule"] == "direct_term" for r in reasons):
            own = rules.keywords.own_computers(text)
        if own:
            out.own_computers += 1
            reasons = [r for r in reasons if r["rule"] != "direct_term"]
        # A term that is no reason by itself counts only beside another that is left.
        reasons = rules.enough(reasons)
        if own and not reasons:
            continue
        if not reasons:
            out.no_reason += 1
            continue
        if day is None:
            out.undated += 1
            continue
        if fips is None:
            out.out_of_scope += 1
            continue
        # A moratorium or an ordinance about data centers uses the words too. The reviewer is
        # told which words of rule making sit in the item. The signal is the same.
        beside = (
            rules.keywords.rule_making(text)
            if any(r["rule"] == "direct_term" for r in reasons)
            else []
        )
        number = (item.get("number") or "").rstrip(".") or f"in position {item.get('sequence')}"
        file = f", file {item['file']}" if item.get("file") else ""
        terms = ", ".join(f'"{t}"' for t in dict.fromkeys(r["term"] for r in reasons))
        hits = [
            h
            for h in rules.keywords.find(text)
            if (h.kind != "project_code_name" or negotiations)
            and not (own and h.kind == "direct_term")
        ]
        out.drafts.append(
            Draft(
                signal_type="agenda_keyword",
                key=f"legistar:{agenda['client']}:{agenda['event_id']}:{item.get('id')}",
                event_date=day,
                summary=(
                    f"The agenda of the {who} for {_long_date(day)} has an item that uses "
                    f"the words {terms}: item {number}{file}."
                ),
                confidence=rules.how_sure(reasons),
                county_fips=fips,
                party=None,
                party_kind=None,
                extracted={
                    "reasons": reasons,
                    "reference": f"{who}, meeting of {_long_date(day)}, item {number}{file}",
                    "page": agenda.get("page") or "",
                    "body": who,
                    "item": {
                        "number": item.get("number") or "",
                        "file": item.get("file") or "",
                        "type": item.get("type") or "",
                    },
                    "snippets": _narrow_snippets(text, hits),
                    "counties": named,
                    "meeting": _meeting(str(agenda["government"]), day, reasons),
                    **_set_aside(own),
                    **_rule_making(beside),
                },
            )
        )
    return out


# --- agenda files from governments' own sites ---------------------------------------------------

_MINUTES_NOT_AGENDA = re.compile(r"\bminutes\b", re.IGNORECASE)
_AGENDA_WORD = re.compile(r"agenda", re.IGNORECASE)
_TOP = 3000  # an agenda names itself and its meeting's date near the top


_BEFORE = 400


def _counts_in_a_file(hit: Hit, passage: str) -> bool:
    if hit.kind != "project_code_name":
        return True
    return "\n" not in hit.text and bool(
        _NEGOTIATIONS.search(passage[max(0, hit.start - _BEFORE) : hit.end])
    )


def agenda_file(doc: Doc, rules: Rules) -> Outcome:
    """One signal for an agenda file that uses a term the radar looks for.

    The file is a PDF or a Word file with no items to tell apart, so a file gives one signal.
    An agenda names people, and so can its file name. The summary names the government, the
    meeting's date and the words that matched, and nothing else. The words around each match
    and the pages they are on are kept beside the signal for the reviewer.
    """
    out = Outcome()
    meta = doc.meta
    if meta.get("record") != "agenda_file":
        return out  # the list of links on an agenda page holds nothing to read
    out.records = 1
    text = doc.text or ""
    if not text.strip():
        out.no_text = 1
        return out
    top = text[:_TOP]
    if _MINUTES_NOT_AGENDA.search(top) and not _AGENDA_WORD.search(top):
        out.no_reason = 1  # the minutes of a meeting, posted where agendas are
        return out
    found: list[tuple[int, str, list[Hit]]] = []
    own = None  # the word that showed an item to be about the government's own computers
    beside: list[str] = []  # the words of rule making in an item that says "data center"
    for number, (_, passage) in enumerate(_passages(text), 1):
        hits = []
        for hit in rules.keywords.find(passage):
            if not _counts_in_a_file(hit, passage):
                continue
            if hit.kind == "direct_term":
                item = _agenda_item(passage, hit.start, hit.end)
                shows = rules.keywords.own_computers(item)
                if shows:
                    own = own or shows
                    continue
                beside += [w for w in rules.keywords.rule_making(item) if w not in beside]
            hits.append(hit)
        if hits:
            found.append((number, passage, hits))
    if own:
        out.own_computers = 1
    # A term that is no reason by itself counts only beside another, anywhere in the file.
    if not rules.keywords.stands_alone(hit.term for _, _, hits in found for hit in hits):
        found = []
    if not found:
        out.no_reason = 0 if own else 1
        return out
    day, date_from = _iso_date(str(meta.get("meeting_date") or "")), meta.get("date_from")
    if day is None:
        # The page gave no date. An agenda states its meeting's date at its head.
        day, date_from = find_date(top, doc.retrieved_at.date()), "file_text"
    if day is None:
        out.undated = 1
        return out
    counties = _counties_of(doc, rules)
    named = [str(c) for c in meta.get("counties") or []]
    in_scope = [f for f in (counties.fips(name) for name in named) if f]
    if not in_scope:
        out.out_of_scope = 1
        return out
    fips = out.county_fips = in_scope[0]

    reasons: list[dict] = []
    snippets: list[str] = []
    for _, passage, hits in found:
        for hit in hits:
            reason = {"rule": hit.kind, "term": hit.term, "field": "text", "text": hit.text}
            if reason not in reasons:
                reasons.append(reason)
        for piece in _narrow_snippets(passage, hits):
            if piece not in snippets:
                snippets.append(piece)
    place = place_name(str(meta["government"]))
    terms = ", ".join(f'"{t}"' for t in dict.fromkeys(r["term"] for r in reasons))
    out.drafts.append(
        Draft(
            signal_type="agenda_keyword",
            key=f"agenda_file:{doc.url.split('?')[0]}",
            event_date=day,
            summary=(
                f"An agenda that {place} posted for a meeting of {_long_date(day)} uses "
                f"the words {terms}."
            ),
            confidence=rules.how_sure(reasons),
            county_fips=fips,
            party=None,
            party_kind=None,
            extracted={
                "reasons": reasons,
                "reference": f"{place}, agenda for the meeting of {_long_date(day)}",
                "page": meta.get("page") or "",
                "bodies_on_page": [str(b) for b in meta.get("bodies") or []],
                "date_from": date_from,
                "pages_with_terms": [number for number, _, _ in found][:MAX_EVIDENCE],
                "snippets": snippets[:MAX_EVIDENCE],
                "counties": named,
                "meeting": _meeting(str(meta["government"]), day, reasons),
                **_set_aside(own),
                **_rule_making(beside),
            },
        )
    )
    return out


PROCESSORS: dict[str, Processor] = {
    "tx_tceq_air_pending_legacy": tceq_air_pending,
    "tx_twdb_well_reports": twdb_well_reports_extract,
    "tx_ercot_rpg": ercot_rpg_file,
    "tx_agendas_legistar": legistar_agenda,
    "tx_agendas_own_sites": agenda_file,
    # Michigan's agendas are read by the same two processors. BUILD_PLAN.md milestone M11.
    "mi_agendas_legistar": legistar_agenda,
    "mi_agendas_own_sites": agenda_file,
}


SCAN_NOTE = "The file is a scan, read by character recognition."


def _mark_scan(draft: Draft, read: dict) -> Draft:
    """A signal whose words a machine read from a picture says so, to the public and to the
    reviewer. The reviewer opens the scan itself."""
    draft.extracted["text_from"] = "ocr"
    draft.extracted["ocr"] = {
        key: read.get(key)
        for key in (
            "engine",
            "confidence",
            "doubtful_words",
            "words",
            "pages_read",
            "pages_in_file",
        )
    }
    return dataclasses.replace(draft, summary=f"{draft.summary} {SCAN_NOTE}")


def process(doc: Doc, rules: Rules) -> Outcome:
    outcome = PROCESSORS[doc.source_id](doc, rules)
    read = doc.meta.get("ocr")
    if isinstance(read, dict):
        outcome.drafts = [_mark_scan(draft, read) for draft in outcome.drafts]
    for draft in outcome.drafts:
        if draft.signal_type not in rules.signal_types:
            raise ValueError(f"{draft.signal_type} is not a signal type in config/scoring.yaml")
    return outcome
