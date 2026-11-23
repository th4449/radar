"""Read stored documents and write their signals. See BUILD_PLAN.md milestone M4.

    uv run python -m pipeline.process

needs DATABASE_URL and an archive, the same settings a real collector run needs.

Each run reads every document its rules have not read yet, oldest first, so a fact belongs to
the first document that showed it. A list is collected again every week, and the same row in a
later copy makes no second signal. The run then groups signals into sites and scores every
site.

When a rule, a keyword, a listed name or the Comptroller's list changes, the rules get a new
version and every document is read again. Reading again only adds signals. It never removes
one, because a reviewer may already have acted on it.

A run is logged, success or failure. A document that cannot be read is counted as an error and
left for the next run. The other documents are still read.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field

import psycopg

from collectors.base import ArchiveStore, Fetcher, LayoutChanged, NotPermitted
from collectors.hosted_archive import NotConfigured as ArchiveNotConfigured
from collectors.hosted_archive import archive_from_env
from pipeline import tceq_applications
from pipeline.config import CONFIG_DIR, ScoringFile, load_sources
from pipeline.entities import canonical_name, match_key
from pipeline.geocode import ArchivedLookup
from pipeline.signals import (
    LISTING_SOURCE,
    PROCESSORS,
    RULES_VERSION,
    Doc,
    Draft,
    Rules,
    process,
    read_listings,
)
from pipeline.sites import update_sites
from pipeline.store import PostgresSink
from pipeline.triage import NotConfigured, PostgresLedger, Triager, annotate

MAX_HELD_REFS = 200
MAX_ERRORS_KEPT = 50


@dataclass
class ProcessSummary:
    rules_version: str
    status: str = "running"  # ok, partial or failed
    documents: int = 0
    signals_new: int = 0
    held_back: int = 0
    errors: int = 0
    error: str | None = None
    detail: dict = field(default_factory=dict)


def load_rules(conn: psycopg.Connection, store: ArchiveStore) -> Rules:
    """The rules, with the newest stored copy of the Comptroller's list."""
    row = conn.execute(
        """select d.storage_path, d.sha256
           from public.documents d join public.sources s on s.id = d.source_id
           where s.slug = %s
           order by d.retrieved_at desc, d.id desc
           limit 1""",
        [LISTING_SOURCE],
    ).fetchone()
    if row is None:
        return Rules(listings={})
    return Rules(listings=read_listings(store.get(row[0])), listings_sha256=row[1])


def rules_version(rules: Rules) -> str:
    """Changes whenever anything a processor consults changes."""
    digest = hashlib.sha256(RULES_VERSION.encode())
    for name in ("keywords.yaml", "entities.yaml", "counties_tx.yaml", "counties_mi.yaml"):
        digest.update((CONFIG_DIR / name).read_bytes())
    digest.update(json.dumps(rules.confidence, sort_keys=True).encode())
    digest.update((rules.listings_sha256 or "no list").encode())
    return f"{RULES_VERSION}+{digest.hexdigest()[:12]}"


def _entity_id(conn: psycopg.Connection, draft: Draft) -> int | None:
    if not draft.party:
        return None
    return conn.execute(
        """insert into public.entities (name, normalized_name, match_key, kind)
           values (%s, %s, %s, %s)
           on conflict (normalized_name) do update set match_key = excluded.match_key
           returning id""",
        [draft.party, canonical_name(draft.party), match_key(draft.party), draft.party_kind],
    ).fetchone()[0]


def _save(conn: psycopg.Connection, document_id: int, doc: Doc, draft: Draft, version: str) -> bool:
    """Store one signal. False when the same fact is already stored."""
    row = conn.execute(
        """insert into public.signals
             (document_id, signal_type, event_date, summary, entity_id, confidence, extracted,
              fingerprint, county_fips)
           values (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
           on conflict (fingerprint) do nothing
           returning id""",
        [
            document_id, draft.signal_type, draft.event_date, draft.summary,
            _entity_id(conn, draft), draft.confidence,
            json.dumps({**draft.extracted, "rules_version": version}),
            draft.fingerprint(doc.source_id), draft.county_fips,
        ],
    ).fetchone()  # fmt: skip
    return row is not None


def run(
    conn: psycopg.Connection,
    store: ArchiveStore,
    *,
    runner: str | None = None,
    limit: int | None = None,
    rules: Rules | None = None,
    triager: Triager | None = None,
    as_of: dt.date | None = None,
    enrich: Callable[[], dict] | None = None,
    scoring: ScoringFile | None = None,
) -> ProcessSummary:
    rules = rules or load_rules(conn, store)
    version = rules_version(rules)
    summary = ProcessSummary(version)
    summary.detail = {"by_source": {}, "held_refs": [], "errors": []}
    if rules.listings_sha256 is None:
        summary.detail["note"] = "No copy of the Comptroller's data center list is stored."
    run_id = conn.execute(
        "insert into public.processing_runs (rules_version, runner) values (%s, %s) returning id",
        [version, runner],
    ).fetchone()[0]
    try:
        waiting = conn.execute(
            """select d.id, s.slug, d.url, d.retrieved_at, d.sha256, d.storage_path,
                      coalesce(d.text, ''), d.raw_meta
               from public.documents d join public.sources s on s.id = d.source_id
               where s.slug = any(%s) and d.processed_version is distinct from %s
               order by d.retrieved_at, d.id
               limit %s""",
            [sorted(PROCESSORS), version, limit],
        ).fetchall()
        for document_id, slug, url, retrieved_at, sha256, storage_path, text, meta in waiting:
            try:
                doc = Doc(slug, url, retrieved_at, sha256, text, meta, store.get(storage_path))
                outcome = process(doc, rules)
                drafts = annotate(slug, outcome.drafts, triager, document_id)
                with conn.transaction():
                    new = sum(_save(conn, document_id, doc, d, version) for d in drafts)
                    conn.execute(
                        """update public.documents
                           set processed_at = now(), processed_version = %s,
                               county_fips = coalesce(county_fips, %s)
                           where id = %s""",
                        [version, outcome.county_fips, document_id],
                    )
            except (LayoutChanged, OSError, UnicodeDecodeError, ValueError) as exc:
                # Left unread, so the next run tries again once a person has looked.
                summary.errors += 1
                summary.error = f"document {document_id}: {exc}"
                if len(summary.detail["errors"]) < MAX_ERRORS_KEPT:
                    summary.detail["errors"].append({"document_id": document_id, "error": str(exc)})
                continue
            summary.documents += 1
            summary.signals_new += new
            summary.held_back += outcome.held_back
            totals = summary.detail["by_source"].setdefault(slug, {"documents": 0, "new": 0})
            totals["documents"] += 1
            totals["new"] += new
            for name, count in outcome.counts().items():
                totals[name] = totals.get(name, 0) + count
            room = MAX_HELD_REFS - len(summary.detail["held_refs"])
            summary.detail["held_refs"].extend(
                ref for ref in outcome.held_refs[:room] if ref not in summary.detail["held_refs"]
            )
        # Air permit signals get their county from the application file each row links.
        if enrich is not None:
            with conn.transaction():
                summary.detail["tceq_applications"] = enrich()
        # Sites are grouped and scored on every run, new documents or not: scores decay.
        with conn.transaction():
            summary.detail["sites"] = update_sites(conn, as_of=as_of, scoring=scoring)
        if triager is not None:
            summary.detail["triage"] = {
                "calls": triager.calls,
                "skipped_for_cap": triager.skipped_for_cap,
                "cap_usd": str(triager.cap_usd),
            }
        if summary.errors == 0:
            summary.status = "ok"
        else:
            summary.status = "partial" if summary.documents else "failed"
    except Exception as exc:
        summary.status = "failed"
        summary.error = repr(exc)
        raise
    finally:
        conn.execute(
            """update public.processing_runs
               set finished_at = now(), status = %s, documents = %s, signals_new = %s,
                   held_back = %s, errors = %s, error = %s, detail = %s::jsonb
               where id = %s""",
            [summary.status, summary.documents, summary.signals_new, summary.held_back,
             summary.errors, summary.error, json.dumps(summary.detail), run_id],
        )  # fmt: skip
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read stored documents and write their signals.")
    parser.add_argument("--limit", type=int, help="read at most this many documents")
    parser.add_argument(
        "--fetch-applications",
        action="store_true",
        help="fetch the TCEQ application file of each air permit signal that has no county. "
        "Needs RADAR_CONTACT.",
    )
    parser.add_argument("--runner", default=os.environ.get("RADAR_RUNNER", "manual"))
    args = parser.parse_args(argv)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("not started: set DATABASE_URL and an archive", file=sys.stderr)
        return 2
    try:
        store = archive_from_env()
    except ArchiveNotConfigured as exc:
        print(f"not started: {exc}", file=sys.stderr)
        return 2
    with psycopg.connect(database_url, autocommit=True) as conn:
        try:
            triager = Triager.from_env(PostgresLedger(conn))
        except NotConfigured as exc:
            print(f"not started: {exc}", file=sys.stderr)
            return 2
        if not args.fetch_applications:
            summary = run(conn, store, runner=args.runner, limit=args.limit, triager=triager)
        else:
            source = load_sources().by_id(tceq_applications.SOURCE_ID)
            sink = PostgresSink(conn)
            try:
                fetcher = Fetcher(source)
            except NotPermitted as exc:
                print(f"not started: {exc}", file=sys.stderr)
                return 2
            with fetcher:
                lookup = ArchivedLookup(source, fetcher, store, sink)
                summary = run(
                    conn,
                    store,
                    runner=args.runner,
                    limit=args.limit,
                    triager=triager,
                    enrich=lambda: tceq_applications.enrich_air_permits(
                        conn, source=source, lookup=lookup, sink=sink
                    ),
                )
    print(json.dumps(dataclasses.asdict(summary), indent=2))
    return 0 if summary.status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
