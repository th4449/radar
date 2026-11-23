"""Stored history, read as dated signals for the backtest. BUILD_PLAN.md milestone M9.

A history run stores older records. This module reads them with the rules of
pipeline/signals.py and hands the harness one dated signal for each fact. It writes nothing.

Three things here are the backtest's own and are not how the everyday pipeline works.

- **The counties read are the 30 test counties and the control counties.** The radar does not
  watch a control county. The backtest reads it on the statewide feeds to count false alarms.
- **A signal counts from the day its record could be seen,** worked out for each source in
  `seen_on()`. Where that day is not recorded, the later bound is taken, so a lead time is
  never overstated.
- **A company counts as listed only from the day its registration took effect.** The stored
  copy of the Comptroller's list is today's. A company that registered in 2026 was not on the
  list anyone could read in 2024.

It also says which known project a record names, which the everyday pipeline cannot do: an
agenda names people, so its signal carries no company. Here the words around the matched term
are searched for the companies and code names of the known projects in the same county. The
words themselves are never kept. See `ProjectNames`.

Nothing in this module touches the network.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

import psycopg

from backtest.harness import Project, Signal
from backtest.projects import KnownProject, to_project
from collectors.base import ArchiveStore, LayoutChanged
from collectors.tx import comptroller_data_centers
from pipeline.config import CountiesFile, load_all_counties, load_control_counties, load_counties
from pipeline.counties import CountyIndex
from pipeline.entities import canonical_name, classify_party, match_key
from pipeline.signals import PROCESSORS, Doc, Draft, Listing, Rules, process, read_listings
from pipeline.sites import _names, _point

# The words on each side of a matched term that are searched for a known project's name. An
# agenda item is seldom longer.
NEAR_TERM = 500

_LISTED_RULES = ("listed_company", "listed_company_loose")
# A development corporation ends in a legal form, so the everyday rules call it a company.
# Here it is a public body: it is on its own government's agenda every month.
_PUBLIC_IN_A_NAME = (
    " ECONOMIC DEVELOPMENT ",
    " INDUSTRIAL DEVELOPMENT ",
    " EDUCATION SERVICE CENTER ",
)
_PARENTHESES = re.compile(r"\([^)]*\)")
_NOT_A_WORD = re.compile(r"[^A-Z0-9]+")


def history_rules(
    listing: bytes | None, *, listings: dict[str, list[Listing]] | None = None
) -> Rules:
    """The everyday rules, reading the test counties and the control counties."""
    if listings is None:
        listings = read_listings(listing) if listing else {}
    rules = Rules(listings=listings, listings_sha256="the copy the backtest was given")
    test, control = load_counties("TX"), load_control_counties("TX")
    scope = CountiesFile(state="TX", counties=[*test.counties, *control.counties])
    rules.counties["TX"] = CountyIndex(scope, load_all_counties("TX"))
    return rules


def listed_since(listing: bytes) -> dict[tuple[str, str], dt.date | None]:
    """The day each registration on the Comptroller's list took effect, by program and name.

    None where the state typed a date that cannot be read.
    """
    out: dict[tuple[str, str], dt.date | None] = {}
    for reg in comptroller_data_centers.parse(listing):
        key = (reg.program, reg.name)
        days = [d for d in (out.get(key), reg.effective_date) if d is not None]
        out[key] = min(days) if days else None
    return out


# --- the day a record could be seen -------------------------------------------------------------


def _day(text: object) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(text or "")[:10])
    except ValueError:
        return None


def seen_on(doc: Doc, draft: Draft) -> tuple[dt.date, str]:
    """The first day the record could be seen, and why that day."""
    if doc.source_id == "tx_agendas_legistar":
        published = _day(json.loads(doc.body).get("agenda_published"))
        if published is not None and published <= draft.event_date:
            return published, "the day Legistar says the agenda was last published"
        return draft.event_date, "the day of the meeting: no earlier publishing day is recorded"
    if doc.source_id == "tx_agendas_own_sites":
        return draft.event_date, "the day of the meeting: the day the file was posted is not kept"
    if doc.source_id == "tx_twdb_well_reports":
        return draft.event_date, "the day the report was submitted to the state"
    if doc.source_id == "tx_ercot_rpg":
        return draft.event_date, "the day in the file's address, the day ERCOT posted it"
    # A pending list shows what is pending today. The day a row joined it is not recorded.
    return doc.retrieved_at.date(), "the day the radar first held the list"


# --- which known project a record names ---------------------------------------------------------


def _words(text: str) -> str:
    """Capitals, one space between words, a space at each end: for whole-word search."""
    upper = text.upper().replace("&", " AND ")
    upper = re.sub(r"[.'’`]", "", upper)
    return f" {_NOT_A_WORD.sub(' ', upper).strip()} "


def _public_body(name: str) -> bool:
    if classify_party(name).kind == "public_body":
        return True
    return any(phrase in _words(name) for phrase in _PUBLIC_IN_A_NAME)


@dataclass(frozen=True)
class _Name:
    words: str  # as _words() gives it
    project: str
    label: str  # "company Example LLC" or "code name Project Falcon"
    counts_alone: bool  # without the words "data center" beside it


class ProjectNames:
    """The names that tie a record to a known project, by county.

    - A company's name without its legal form, and a project's code names.
    - **A company's name counts only beside the words "data center".** The list of known
      projects names engineers, lenders and tenants too, and Microsoft sells software to
      every county. A rezoning that names a project's engineer is not that project.
    - **A code name that starts with "Project" counts on its own.** Any other code name is
      treated as a company's name is.
    - **A public body is never such a name.** A development corporation is on its own
      government's agenda every month.
    - A name counts only in the project's own county.
    - When a record carries a name only one project has, that project is the one it names. A
      name two projects share names both, and the harness then gives the signal to neither.
    """

    def __init__(self, projects: Iterable[KnownProject]) -> None:
        self._by_county: dict[str, list[_Name]] = {}
        fips = {c.name: c.fips for c in load_counties("TX").counties}
        for project in projects:
            names = self._by_county.setdefault(fips[project.county], [])
            for company in project.companies:
                plain = _PARENTHESES.sub(" ", company).strip()
                if not plain or _public_body(plain):
                    continue
                words = _words(match_key(plain))
                if words.strip():
                    names.append(_Name(words, project.key, f"company {plain}", False))
            for code_name in project.code_names:
                words = _words(code_name)
                if words.strip():
                    alone = words.startswith(" PROJECT ") and len(words.split()) > 1
                    names.append(_Name(words, project.key, f"code name {code_name}", alone))

    def company_keys(self, project: str, county_fips: str) -> list[str]:
        return [
            n.words.strip()
            for n in self._by_county.get(county_fips, [])
            if n.project == project and n.label.startswith("company ")
        ]

    def find(self, near_any_term: str, near_direct_term: str, county_fips: str | None):
        """The names a record carries, given the words near its terms."""
        here = self._by_county.get(county_fips or "", [])
        anywhere, direct = _words(near_any_term), _words(near_direct_term)
        found = [n for n in here if n.words in (anywhere if n.counts_alone else direct)]
        holders: dict[str, set[str]] = {}
        for n in here:
            holders.setdefault(n.words, set()).add(n.project)
        alone = [n for n in found if len(holders[n.words]) == 1]
        return alone or found


def _near_terms(text: str, terms: set[str], rules: Rules) -> str:
    """The words around each matched term, joined."""
    pieces = [
        text[max(0, hit.start - NEAR_TERM) : hit.end + NEAR_TERM]
        for hit in rules.keywords.find(text)
        if hit.term in terms
    ]
    return "\n".join(pieces)


def _searched(doc: Doc, draft: Draft, rules: Rules, *, direct_only: bool) -> str:
    """The words of the record that are searched for a known project's name. Never kept."""
    reasons = draft.extracted.get("reasons") or []
    terms = {
        r["term"]
        for r in reasons
        if r.get("term") and (r["rule"] == "direct_term" or not direct_only)
    }
    if direct_only and not terms:
        return ""
    if doc.source_id == "tx_agendas_legistar":
        wanted = draft.key.rsplit(":", 1)[-1]
        for item in json.loads(doc.body)["items"]:
            if str(item.get("id")) == wanted:
                return f"{item.get('title') or ''} {item.get('note') or ''}"
        return ""
    if doc.source_id in ("tx_agendas_own_sites", "tx_ercot_rpg"):
        return _near_terms(doc.text or "", terms, rules)
    row = draft.extracted.get("row") or {}
    free = draft.extracted.get("free_text_matches") or {}
    pieces = [draft.party or "", *(str(v) for v in row.values())]
    pieces += [piece for found in free.values() for piece in found]
    return " ".join(pieces)


# --- reading ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Record:
    """One signal from stored history, and what the report says of it.

    It keeps the reference, the terms and the company a record names. It never keeps the
    words of an agenda, which can name a person.
    """

    signal: Signal
    document_id: int
    reference: str
    url: str
    rule: str  # the strongest reason
    terms: tuple[str, ...]
    party: str | None
    seen_basis: str
    names_projects: tuple[str, ...]
    named_by: tuple[str, ...]


@dataclass(frozen=True)
class Meeting:
    """One agenda that was read, whether or not it gave a signal."""

    source_id: str
    government: str
    counties: tuple[str, ...]  # FIPS codes
    day: dt.date


def _meeting(doc: Doc, rules: Rules) -> Meeting | None:
    record = doc.meta.get("record")
    if record == "legistar_agenda":
        day = _day(doc.meta.get("event_date"))
    elif record == "agenda_file":
        day = _day(doc.meta.get("meeting_date"))
    else:
        return None
    if day is None:
        return None
    counties = rules.counties["TX"]
    fips = tuple(f for f in (counties.fips(str(c)) for c in doc.meta.get("counties") or []) if f)
    return Meeting(doc.source_id, str(doc.meta.get("government") or ""), fips, day)


@dataclass
class History:
    records: list[Record] = field(default_factory=list)
    meetings: list[Meeting] = field(default_factory=list)
    counts: dict[str, dict[str, int]] = field(default_factory=dict)  # by source
    entity_ids: dict[str, int] = field(default_factory=dict)  # canonical name -> id
    parties: dict[int, str] = field(default_factory=dict)  # id -> the name as first written
    listed_later: int = 0  # records whose only reason was a listing that came after them
    read_through: dt.date | None = None  # the newest day a document was retrieved
    errors: list[tuple[int, str]] = field(default_factory=list)

    @property
    def signals(self) -> list[Signal]:
        return [r.signal for r in self.records]


def _as_listed_then(
    draft: Draft, rules: Rules, since: Mapping[tuple[str, str], dt.date | None]
) -> Draft | None:
    """The draft with a listing that came after the record taken out. None if nothing is left."""
    reasons = draft.extracted.get("reasons") or []
    if not any(r["rule"] in _LISTED_RULES for r in reasons) or not draft.party:
        return draft
    days = [since.get((x.program, x.data_center)) for x in rules.listings_for(draft.party)]
    days = [d for d in days if d is not None]
    if days and min(days) <= draft.event_date:
        return draft
    kept = [r for r in reasons if r["rule"] not in _LISTED_RULES]
    if not kept:
        return None
    return dataclasses.replace(
        draft, confidence=rules.how_sure(kept), extracted={**draft.extracted, "reasons": kept}
    )


def read(
    docs: Iterable[tuple[int, Doc]],
    rules: Rules,
    projects: Sequence[KnownProject],
    since: Mapping[tuple[str, str], dt.date | None],
) -> History:
    """Every signal the documents give, oldest document first, each fact once."""
    names = ProjectNames(projects)
    out = History()
    seen: set[str] = set()
    for document_id, doc in docs:
        try:
            outcome = process(doc, rules)
        except (LayoutChanged, OSError, UnicodeDecodeError, ValueError) as exc:
            out.errors.append((document_id, str(exc)))
            continue
        counts = out.counts.setdefault(doc.source_id, {"documents": 0})
        counts["documents"] += 1
        day = doc.retrieved_at.date()
        out.read_through = max(out.read_through or day, day)
        meeting = _meeting(doc, rules)
        if meeting is not None:
            out.meetings.append(meeting)
        for name, count in outcome.counts().items():
            counts[name] = counts.get(name, 0) + count
        for made in outcome.drafts:
            draft = _as_listed_then(made, rules, since)
            if draft is None:
                out.listed_later += 1
                counts["signals"] -= 1
                continue
            fingerprint = draft.fingerprint(doc.source_id)
            if fingerprint in seen:
                counts["signals"] -= 1
                continue
            seen.add(fingerprint)
            reasons = draft.extracted["reasons"]
            rule = max((r["rule"] for r in reasons), key=lambda r: rules.confidence[r])
            entity_id = None
            if draft.party:
                canonical = canonical_name(draft.party)
                entity_id = out.entity_ids.setdefault(canonical, len(out.entity_ids) + 1)
                out.parties.setdefault(entity_id, draft.party)
            found = names.find(
                _searched(doc, draft, rules, direct_only=False),
                _searched(doc, draft, rules, direct_only=True),
                draft.county_fips,
            )
            named = tuple(sorted({n.project for n in found}))
            day, basis = seen_on(doc, draft)
            signal = Signal(
                signal_id=len(out.records) + 1,
                signal_type=draft.signal_type,
                source_id=doc.source_id,
                county_fips=draft.county_fips or "",
                event_date=draft.event_date,
                available_on=day,
                confidence=draft.confidence,
                entity_id=entity_id,
                names=_names(draft.extracted),
                point=_point(draft.extracted),
                names_projects=frozenset(named),
            )
            out.records.append(
                Record(
                    signal=signal,
                    document_id=document_id,
                    reference=str(draft.extracted.get("reference") or ""),
                    url=doc.url,
                    rule=rule,
                    terms=tuple(dict.fromkeys(r["term"] for r in reasons if r.get("term"))),
                    party=draft.party,
                    seen_basis=basis,
                    names_projects=named,
                    named_by=tuple(sorted({n.label for n in found})),
                )
            )
    return out


def harness_projects(projects: Sequence[KnownProject], history: History) -> list[Project]:
    """The known projects, each with the ids of the parties that carry its companies' names.

    A party carries a company's name when the two are the same without their legal forms, or
    the party's name starts with the company's: a project company is often named for its
    parent and a place.
    """
    names = ProjectNames(projects)
    keys = {name: match_key(name) for name in history.entity_ids}
    out = []
    for known in projects:
        project = to_project(known)
        wanted = names.company_keys(known.key, project.county_fips)
        ids = frozenset(
            history.entity_ids[name]
            for name, key in keys.items()
            if any(key == w or key.startswith(w + " ") for w in wanted)
        )
        out.append(dataclasses.replace(project, entity_ids=ids))
    return out


def load(
    conn: psycopg.Connection,
    store: ArchiveStore,
    rules: Rules,
    projects: Sequence[KnownProject],
    since: Mapping[tuple[str, str], dt.date | None],
) -> History:
    """Read every stored document of a source that feeds signals. Writes nothing."""
    rows = conn.execute(
        """select d.id, s.slug, d.url, d.retrieved_at, d.sha256, d.storage_path,
                  coalesce(d.text, ''), d.raw_meta
           from public.documents d join public.sources s on s.id = d.source_id
           where s.slug = any(%s)
           order by d.retrieved_at, d.id""",
        [sorted(PROCESSORS)],
    ).fetchall()

    def docs() -> Iterable[tuple[int, Doc]]:
        for document_id, slug, url, retrieved_at, sha256, storage_path, text, meta in rows:
            body = store.get(storage_path)
            yield document_id, Doc(slug, url, retrieved_at, sha256, text, meta, body)

    return read(docs(), rules, projects, since)
