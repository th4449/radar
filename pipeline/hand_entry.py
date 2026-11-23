"""Enter a record a person read by hand. No request is made.

    uv run python -m pipeline.hand_entry <source-id> <the saved file> \\
        --url <the record's own address> --date 2026-11-28 --county Hood \\
        --type abatement_notice --reference "Notice 4471" \\
        --summary "Hood County published a notice of ..." --party "Example Hosting LLC"

Some sources a program may not read and a person may. A person opens the record at its
source, saves it as a PDF or a web page, and runs this command on the saved file.

**Only a source marked `hand_entered: true` in config/sources.yaml takes a record,** and only
the owner marks one. A source whose terms bar storing its content stays unmarked: entering by
hand is not a way around a site's terms.

What the command checks, before anything is stored:

- The record's address is on the source's own site.
- **The record gives a reason,** as every record must. The words of the saved file are read
  with the radar's own terms. A file that uses none of them needs `--reason`, which says in a
  sentence why the record is a signal. A stated reason counts as the weakest kind does.
- The county is one the radar covers, and the kind of signal is one it scores.
- **A named party shows a company or a public body.** A name that may be a person is refused.
- The record names a company, or its file gives a project name. Otherwise nothing holds it
  to a site and no reviewer would see it.
- The summary restates the record. It may not say planned, approved or coming unless the
  file says so.

What it stores is what a run stores: the file, the record's address, a time and the file's
hash, marked as entered by hand, and one signal with its reason. A reviewer still opens the
record and confirms it before anything is public.

It needs DATABASE_URL and an archive, as a real run does. The exit code is 0 when the record
is stored or was stored before, 1 when it is refused and 2 when the command could not start.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import psycopg

from collectors.base import ArchiveStore, FetchResult, RunSummary, archive
from collectors.hosted_archive import NotConfigured, archive_from_env
from pipeline import process
from pipeline.config import Source, load_sources
from pipeline.extract import extract, sniff
from pipeline.signals import Doc, Draft, Rules
from pipeline.sites import update_sites
from pipeline.store import PostgresSink

RUNNER = "by-hand"
VERSION = "by-hand"
CONTENT_TYPES = {
    "pdf": "application/pdf",
    "html": "text/html",
    "text": "text/plain",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
SUMMARY_LENGTH = (30, 500)
# Words a summary may use only when the file itself uses them.
_CLAIMS = ("planned", "approved", "coming", "will be built", "under construction")


class NotEntered(Exception):
    """The record was not stored."""


@dataclass(frozen=True)
class Facts:
    """What a person read in the record."""

    url: str
    event_date: dt.date
    county: str
    signal_type: str
    summary: str
    reference: str  # the record's own number or title. Never a party's name
    party: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class Prepared:
    result: FetchResult
    draft: Draft
    text: str


def _long_date(day: dt.date) -> str:
    return f"{day:%B} {day.day}, {day.year}"


def _own_site(url: str, source: Source) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    home = (urlsplit(str(source.url)).hostname or "").lower().removeprefix("www.")
    return bool(host) and (host == home or host.endswith("." + home))


def prepare(
    source: Source,
    path: Path,
    facts: Facts,
    rules: Rules,
    *,
    saved_at: dt.datetime,
    now: dt.datetime | None = None,
) -> Prepared:
    """Check the facts against the saved file. Raises NotEntered. Touches no database."""
    now = now or dt.datetime.now(dt.UTC)
    if not source.hand_entered:
        raise NotEntered(
            f"{source.id} is not marked hand_entered in config/sources.yaml. Only a source the "
            "owner has marked takes a record entered by hand."
        )
    if saved_at.tzinfo is None:
        raise NotEntered("the time needs a time zone, such as 2026-12-01T09:30:00-06:00")
    if saved_at > now:
        raise NotEntered(f"the time {saved_at.isoformat()} is in the future")

    body = Path(path).read_bytes()
    if not body:
        raise NotEntered(f"{Path(path).name} is empty")
    kind = sniff(body)
    if kind not in CONTENT_TYPES:
        raise NotEntered(
            f"{Path(path).name} is not a PDF, a web page, a text file or a Word file. "
            "Save the record as one of those."
        )
    text = extract(body, CONTENT_TYPES[kind]).text or ""

    if urlsplit(facts.url).scheme not in ("http", "https"):
        raise NotEntered("the record's address must be a web address")
    if not _own_site(facts.url, source):
        raise NotEntered(f"{facts.url} is not on the source's own site, {source.url}")
    if facts.event_date > now.date():
        raise NotEntered(f"the record's date, {facts.event_date}, is in the future")
    fips = rules.counties[source.state].fips(facts.county)
    if fips is None:
        raise NotEntered(f"{facts.county} is not a county the radar covers in {source.state}")
    if facts.signal_type not in rules.signal_types:
        raise NotEntered(
            f"{facts.signal_type} is not a kind of signal in config/scoring.yaml: "
            f"{', '.join(sorted(rules.signal_types))}"
        )

    summary = " ".join(facts.summary.split())
    if not SUMMARY_LENGTH[0] <= len(summary) <= SUMMARY_LENGTH[1]:
        raise NotEntered(
            f"the summary must be {SUMMARY_LENGTH[0]} to {SUMMARY_LENGTH[1]} characters and "
            "restate the record"
        )
    for claim in _CLAIMS:
        if claim in summary.lower() and claim not in text.lower():
            raise NotEntered(
                f'the summary says "{claim}" and the file does not say so. A summary restates '
                "the record."
            )

    reference = " ".join(facts.reference.split())
    if not reference or len(reference) > 80:
        raise NotEntered("the reference is the record's own number or title, 80 characters at most")
    party = " ".join(facts.party.split()) if facts.party else None
    party_kind = None
    if party:
        if party.lower() in reference.lower():
            raise NotEntered("the reference never names a party. Give the record's own number.")
        found = rules.party(party)
        if not found.usable:
            raise NotEntered(
                "the named party may be a person. The radar keeps only a company or a public body."
            )
        party_kind = found.kind

    # The reason, from the words of the file itself, and from the Comptroller's list.
    reasons: list[dict] = []
    for hit in rules.keywords.find(text):
        reason = {"rule": hit.kind, "term": hit.term, "field": "text"}
        if reason not in reasons:
            reasons.append(reason)
    reasons += [r for r in rules.reasons({}, party) if r not in reasons]
    stated = " ".join(facts.reason.split()) if facts.reason else ""
    if stated:
        reasons.append({"rule": "stated_by_hand", "text": stated})
    if not reasons:
        raise NotEntered(
            "the file uses none of the radar's terms and names no listed company. Give "
            "--reason to say in a sentence why this record is a signal."
        )
    confidence = max(
        rules.confidence.get(r["rule"], rules.confidence["code_word"]) for r in reasons
    )
    code_names = [r for r in reasons if r["rule"] == "project_code_name"]
    if party is None and not code_names:
        raise NotEntered(
            "the record names no company and its file gives no project name, so nothing "
            "would hold it to a site and no reviewer would see it. Give --party."
        )

    result = FetchResult(
        url=facts.url,
        final_url=facts.url,
        status=200,
        content_type=CONTENT_TYPES[kind],
        etag=None,
        last_modified=None,
        body=body,
        retrieved_at=saved_at,
    )
    draft = Draft(
        signal_type=facts.signal_type,
        key=f"by_hand:{facts.url}",
        event_date=facts.event_date,
        summary=summary,
        confidence=confidence,
        county_fips=fips,
        party=party,
        party_kind=party_kind,
        extracted={
            "reasons": reasons,
            "reference": f"{source.name}, {reference}",
            "entered_by_hand": True,
            "record_date": _long_date(facts.event_date),
        },
    )
    return Prepared(result, draft, text)


def enter(
    conn: psycopg.Connection,
    store: ArchiveStore,
    source: Source,
    path: Path,
    facts: Facts,
    *,
    saved_at: dt.datetime,
    now: dt.datetime | None = None,
    rules: Rules | None = None,
) -> dict:
    """Check the record, store its file and its signal, and put the signal on a site."""
    rules = rules or process.load_rules(conn, store)
    ready = prepare(source, path, facts, rules, saved_at=saved_at, now=now)
    sink = PostgresSink(conn)
    summary = RunSummary(source.id, documents_seen=1, detail={"by_hand": True, "record": True})
    run_id = sink.start_run(source, RUNNER)
    try:
        meta = {"by_hand": True, "record": "entered_by_hand", "counties": [facts.county]}
        doc = archive(ready.result, source, store, meta)
        with conn.transaction():
            document_new = sink.save_document(doc)
            document_id = conn.execute(
                """select d.id from public.documents d join public.sources s on s.id = d.source_id
                   where s.slug = %s and d.sha256 = %s""",
                [source.id, doc.sha256],
            ).fetchone()[0]
            stored = Doc(
                source.id, doc.url, doc.retrieved_at, doc.sha256, ready.text, doc.raw_meta,
                ready.result.body,
            )  # fmt: skip
            signal_new = process.store_draft(conn, document_id, stored, ready.draft, VERSION)
            update_sites(conn)
        summary.documents_new = int(document_new)
        summary.status = "ok"
    except Exception as exc:
        summary.status = "failed"
        summary.error = repr(exc)
        raise
    finally:
        sink.finish_run(run_id, summary)
    site = conn.execute(
        """select s.label from public.signals sg join public.sites s on s.id = sg.site_id
           where sg.fingerprint = %s""",
        [ready.draft.fingerprint(source.id)],
    ).fetchone()
    return {
        "source_id": source.id,
        "document_new": document_new,
        "signal_new": signal_new,
        "confidence": ready.draft.confidence,
        "reasons": [r["rule"] for r in ready.draft.extracted["reasons"]],
        "site": site[0] if site else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enter a record a person read by hand.")
    parser.add_argument("source_id", help="the id in config/sources.yaml")
    parser.add_argument("file", type=Path, help="the record, saved as a PDF or a web page")
    parser.add_argument("--url", required=True, help="the record's own address at its source")
    parser.add_argument("--date", required=True, type=dt.date.fromisoformat, metavar="YYYY-MM-DD",
                        help="the date on the record")  # fmt: skip
    parser.add_argument("--county", required=True)
    parser.add_argument("--type", required=True, dest="signal_type", help="the kind of signal")
    parser.add_argument("--summary", required=True, help="one or two sentences restating it")
    parser.add_argument("--reference", required=True, help="the record's own number or title")
    parser.add_argument("--party", help="the company or public body the record names")
    parser.add_argument("--reason", help="why it is a signal, if the file uses none of the terms")
    parser.add_argument("--saved-at", type=dt.datetime.fromisoformat, metavar="TIME",
                        help="when the file was saved. Default: the file's own time")  # fmt: skip
    args = parser.parse_args(argv)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("not started: set DATABASE_URL and an archive", file=sys.stderr)
        return 2
    try:
        store = archive_from_env()
    except NotConfigured as exc:
        print(f"not started: {exc}", file=sys.stderr)
        return 2
    try:
        source = load_sources().by_id(args.source_id)
    except KeyError:
        print(f"no source with id {args.source_id} in config/sources.yaml", file=sys.stderr)
        return 2
    if not args.file.is_file():
        print(f"no file at {args.file}", file=sys.stderr)
        return 2
    saved_at = args.saved_at or dt.datetime.fromtimestamp(args.file.stat().st_mtime, dt.UTC)
    facts = Facts(
        url=args.url, event_date=args.date, county=args.county, signal_type=args.signal_type,
        summary=args.summary, reference=args.reference, party=args.party, reason=args.reason,
    )  # fmt: skip
    try:
        with psycopg.connect(database_url, autocommit=True) as conn:
            made = enter(conn, store, source, args.file, facts, saved_at=saved_at)
    except NotEntered as exc:
        print(f"not entered: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(made, indent=2))
    if made["site"] is None:
        print("The signal is stored and sits on no site yet.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
