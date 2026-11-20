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

import datetime as dt
import hashlib
import posixpath
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from urllib.parse import unquote, urlsplit

from collectors.base import LayoutChanged
from collectors.tx import comptroller_data_centers, tceq_air_pending_legacy, twdb_well_reports
from pipeline.classify import Hit, KeywordRules, snippet
from pipeline.config import load_entities, load_scoring
from pipeline.counties import CountyIndex
from pipeline.entities import Party, canonical_name, classify_party, find_companies, match_key
from pipeline.quantities import find_quantities

# Bump this when a rule in this module changes, so stored documents are read again.
RULES_VERSION = "2026-11-20.2"

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
    county_fips: str | None = None  # set when the whole document is about one county

    def counts(self) -> dict[str, int]:
        return {
            "records": self.records,
            "signals": len(self.drafts),
            "no_reason": self.no_reason,
            "held_back": self.held_back,
            "out_of_scope": self.out_of_scope,
            "undated": self.undated,
        }


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
        return out

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
    return [h for h in rules.keywords.find(text) if h.kind != "project_code_name"]


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
PROCESSORS: dict[str, Processor] = {
    "tx_tceq_air_pending_legacy": tceq_air_pending,
    "tx_twdb_well_reports": twdb_well_reports_extract,
    "tx_ercot_rpg": ercot_rpg_file,
}


def process(doc: Doc, rules: Rules) -> Outcome:
    outcome = PROCESSORS[doc.source_id](doc, rules)
    for draft in outcome.drafts:
        if draft.signal_type not in rules.signal_types:
            raise ValueError(f"{draft.signal_type} is not a signal type in config/scoring.yaml")
    return outcome
