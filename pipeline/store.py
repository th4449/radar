"""Where collector runs and documents are recorded.

MemorySink is for tests and dry runs. PostgresSink writes to the database with the service
role. Every run is logged, success or failure, so a broken collector is noticed within a day.
"""

from __future__ import annotations

import json
from collections.abc import Iterable

import psycopg

from collectors.base import ArchivedDocument, RunSummary
from pipeline.config import Source


class MemorySink:
    def __init__(self) -> None:
        self.runs: dict[int, dict] = {}
        self.documents: dict[tuple[str, str], ArchivedDocument] = {}

    def start_run(self, source: Source, runner: str | None = None) -> int:
        run_id = len(self.runs) + 1
        self.runs[run_id] = {"source_id": source.id, "runner": runner, "status": "running"}
        return run_id

    def save_document(self, doc: ArchivedDocument) -> bool:
        key = (doc.source_id, doc.sha256)
        if key in self.documents:
            return False
        self.documents[key] = doc
        return True

    def known(self, source: Source) -> dict[str, dict]:
        newest: dict[str, ArchivedDocument] = {}
        for doc in self.documents.values():
            if doc.source_id != source.id:
                continue
            if doc.url not in newest or doc.retrieved_at >= newest[doc.url].retrieved_at:
                newest[doc.url] = doc
        return {url: dict(doc.raw_meta) for url, doc in newest.items()}

    def find(self, source: Source, url: str) -> ArchivedDocument | None:
        held = [d for d in self.documents.values() if d.source_id == source.id and d.url == url]
        return max(held, key=lambda d: d.retrieved_at) if held else None

    def finish_run(self, run_id: int, summary: RunSummary) -> None:
        self.runs[run_id].update(
            status=summary.status,
            documents_seen=summary.documents_seen,
            documents_new=summary.documents_new,
            errors=summary.errors,
            error=summary.error,
            detail=summary.detail,
        )


def sync_sources(conn: psycopg.Connection, sources: Iterable[Source]) -> dict[str, int]:
    """Copy config/sources.yaml into the sources table. Returns the database id for each slug."""
    ids: dict[str, int] = {}
    for s in sources:
        row = conn.execute(
            """insert into public.sources
                 (slug, state, name, url, method, cadence, robots_status, verified_at)
               values (%s, %s, %s, %s, %s, %s, %s, %s)
               on conflict (slug) do update set
                 state = excluded.state, name = excluded.name, url = excluded.url,
                 method = excluded.method, cadence = excluded.cadence,
                 robots_status = excluded.robots_status, verified_at = excluded.verified_at
               returning id""",
            [s.id, s.state, s.name, str(s.url), s.method, s.cadence, s.robots_status,
             s.verified_at],
        ).fetchone()  # fmt: skip
        ids[s.id] = row[0]
    return ids


class PostgresSink:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn
        self._source_ids: dict[str, int] = {}
        self._sources: dict[str, Source] = {}

    def _source_db_id(self, source: Source) -> int:
        self._sources[source.id] = source
        if source.id not in self._source_ids:
            self._source_ids.update(sync_sources(self._conn, [source]))
        return self._source_ids[source.id]

    def start_run(self, source: Source, runner: str | None = None) -> int:
        return self._conn.execute(
            "insert into public.collector_runs (source_id, runner) values (%s, %s) returning id",
            [self._source_db_id(source), runner],
        ).fetchone()[0]

    def save_document(self, doc: ArchivedDocument) -> bool:
        source_db_id = self._source_ids[doc.source_id]
        # A list that names people is restricted from the moment it is stored.
        restricted = self._sources[doc.source_id].personal_rows
        row = self._conn.execute(
            """insert into public.documents
                 (source_id, url, retrieved_at, sha256, storage_path, text, raw_meta, restricted)
               values (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
               on conflict (source_id, sha256) do nothing
               returning id""",
            [source_db_id, doc.url, doc.retrieved_at, doc.sha256, doc.storage_path, doc.text,
             json.dumps(doc.raw_meta), restricted],
        ).fetchone()  # fmt: skip
        return row is not None

    def known(self, source: Source) -> dict[str, dict]:
        rows = self._conn.execute(
            """select distinct on (url) url, raw_meta
               from public.documents
               where source_id = %s
               order by url, retrieved_at desc, id desc""",
            [self._source_db_id(source)],
        ).fetchall()
        return {url: meta for url, meta in rows}

    def find(self, source: Source, url: str) -> ArchivedDocument | None:
        row = self._conn.execute(
            """select url, retrieved_at, sha256, storage_path, text, raw_meta
               from public.documents
               where source_id = %s and url = %s
               order by retrieved_at desc, id desc
               limit 1""",
            [self._source_db_id(source), url],
        ).fetchone()
        if row is None:
            return None
        return ArchivedDocument(source.id, row[0], row[1], row[2], row[3], row[4] or "", row[5])

    def finish_run(self, run_id: int, summary: RunSummary) -> None:
        self._conn.execute(
            """update public.collector_runs
               set finished_at = now(), status = %s, documents_seen = %s, documents_new = %s,
                   errors = %s, error = %s, detail = %s::jsonb
               where id = %s""",
            [summary.status, summary.documents_seen, summary.documents_new, summary.errors,
             summary.error, json.dumps(summary.detail), run_id],
        )  # fmt: skip
