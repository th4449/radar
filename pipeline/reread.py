"""Note which pages of a stored PDF hold no words, for files stored before the note was kept.

    uv run python -m pipeline.reread            says what it would do and writes nothing
    uv run python -m pipeline.reread --write

needs DATABASE_URL and an archive, the same settings a real collector run needs.

A page with no words, such as a scanned insert in a packet, adds nothing to a file's stored
text. So the third piece of the text is not known to be the third page. Since November 24, 2026
the archive step notes those pages with each PDF, as `pages_without_text`, and the agenda
processor gives the file's own page numbers. A file stored before that day carries no note.
This job writes it.

For each PDF with text and no note:

  - Where the text has a piece for every page of the file, no page was dropped. The note is
    empty and the file is not opened. The extractor joins the pages with a blank line and
    leaves none inside a page, so the count is exact.
  - Otherwise the file is read again from the archive with the extractor. The note is written
    only if what it reads now is the stored text, to the letter, with the same count of pages.
    A file that reads differently today is left as it is and counted.

A signal already made from the file holds the old numbers, which are the numbers of the pieces.
They are changed to the file's own page numbers in the same step, and the signal is marked.
Nothing else about a signal changes: not its summary, its reasons or its site.

No stored text changes. No file is fetched from any site. The job writes one note to a document
once, so it can be stopped and started again.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass, field

import psycopg

from collectors.base import ArchiveStore, sha256_hex
from collectors.hosted_archive import NotConfigured, archive_from_env
from pipeline.extract import extract
from pipeline.signals import file_pages, text_pieces

NOTE = "pages_without_text"
MAX_LEFT_KEPT = 200

# Why a file was left without a note. Each is counted in the summary.
NO_PAGE_COUNT = "its pages were never counted"
NO_TEXT = "it has no text, so nothing in it is given a page"
NOT_IN_ARCHIVE = "its file is not in the archive"
WRONG_FILE = "the file in the archive is not the one that was stored"
NOT_A_PDF_NOW = "it does not read as a PDF with text today"
PAGES_DIFFER = "it has another count of pages today"
TEXT_DIFFERS = "it reads differently today"


@dataclass
class RereadSummary:
    wrote: bool
    documents: int = 0  # PDFs with no note
    noted_unopened: int = 0  # a piece of text for every page
    read_again: int = 0  # files opened
    noted_after_reading: int = 0
    with_a_page_without_words: int = 0
    signals_checked: int = 0
    signals_changed: int = 0
    left: dict[str, int] = field(default_factory=dict)
    left_documents: dict[str, list[int]] = field(default_factory=dict)  # ids, never names


def decide(meta: dict, text: str, sha256: str, read_file) -> tuple[list[int] | None, str | None]:
    """The note for one stored PDF, or why it gets none. `read_file` returns the stored file.

    Returns (note, None), or (None, reason). The file is opened only when it must be.
    """
    pages = meta.get("pages")
    if not isinstance(pages, int) or isinstance(pages, bool):
        return None, NO_PAGE_COUNT
    if not (text or "").strip():
        return None, NO_TEXT
    if not meta.get("members") and text_pieces(text) == pages:
        return [], None
    try:
        body = read_file()
    except OSError:
        return None, NOT_IN_ARCHIVE
    if sha256_hex(body) != sha256:
        return None, WRONG_FILE
    read = extract(body, meta.get("content_type"))
    if read.kind != "pdf" or read.blank_pages is None:
        return None, NOT_A_PDF_NOW
    if read.pages != pages:
        return None, PAGES_DIFFER
    if read.text != text:
        return None, TEXT_DIFFERS
    return list(read.blank_pages), None


def renumbered(piece_numbers: list, meta: dict, text: str) -> list[int]:
    """A signal's stored numbers, which counted pieces of the text, as the file's own pages.

    `meta` carries the note. A piece past the file's own pages is the text of a file attached
    inside it and has no page.
    """
    numbers, _ = file_pages(meta, text_pieces(text))
    out = []
    for n in piece_numbers:
        if isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= len(numbers):
            page = numbers[n - 1]
            if page is not None:
                out.append(page)
    return out


def reread(
    conn: psycopg.Connection,
    store: ArchiveStore,
    *,
    write: bool = False,
    source: str | None = None,
    limit: int | None = None,
    today: dt.date | None = None,
    progress=None,
) -> RereadSummary:
    """Note the pages with no words on every stored PDF that has no note. See the module's top."""
    today = today or dt.datetime.now(dt.UTC).date()
    summary = RereadSummary(wrote=write)
    ids = [
        row[0]
        for row in conn.execute(
            """select d.id
               from public.documents d join public.sources s on s.id = d.source_id
               where d.raw_meta->>'kind' = 'pdf' and not d.raw_meta ? %s
                 and (%s::text is null or s.slug = %s)
               order by d.id
               limit %s""",
            [NOTE, source, source, limit],
        ).fetchall()
    ]
    left: Counter[str] = Counter()
    for document_id in ids:
        sha256, storage_path, meta, text = conn.execute(
            "select sha256, storage_path, raw_meta, text from public.documents where id = %s",
            [document_id],
        ).fetchone()
        summary.documents += 1
        opened = False

        def read_file(path=storage_path):
            nonlocal opened
            opened = True
            if not path:
                raise FileNotFoundError("no storage path")
            return store.get(path)

        try:
            note, why = decide(meta, text or "", sha256, read_file)
        except Exception as exc:  # noqa: BLE001 - one damaged file must not stop the rest
            note, why = None, f"it could not be read: {type(exc).__name__}"
        summary.read_again += opened
        if progress:
            progress(summary)
        if note is None:
            left[why] += 1
            kept = summary.left_documents.setdefault(why, [])
            if len(kept) < MAX_LEFT_KEPT:
                kept.append(document_id)
            continue
        if opened:
            summary.noted_after_reading += 1
        else:
            summary.noted_unopened += 1
        summary.with_a_page_without_words += bool(note)

        noted = {**meta, NOTE: note}
        stamp = {NOTE: note, "pages_noted": {"on": today.isoformat(), "file_read_again": opened}}
        signals = conn.execute(
            """select id, extracted from public.signals
               where document_id = %s and extracted ? 'pages_with_terms'""",
            [document_id],
        ).fetchall()
        changes = []
        for signal_id, extracted in signals:
            summary.signals_checked += 1
            old = extracted.get("pages_with_terms") or []
            new = renumbered(old, noted, text or "")
            change = {"pages_with_terms": new, "pages_exact": True}
            if new != old:
                summary.signals_changed += 1
                change["pages_renumbered"] = {"on": today.isoformat(), "from": old}
            changes.append((signal_id, change))
        if not write:
            continue
        with conn.transaction():
            done = conn.execute(
                """update public.documents set raw_meta = raw_meta || %s::jsonb
                   where id = %s and not raw_meta ? %s""",
                [json.dumps(stamp), document_id, NOTE],
            ).rowcount
            if done:
                for signal_id, change in changes:
                    conn.execute(
                        """update public.signals set extracted = extracted || %s::jsonb
                           where id = %s""",
                        [json.dumps(change), signal_id],
                    )
    summary.left = dict(left)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Note which pages of each stored PDF hold no words. Writes nothing unless "
        "--write is given."
    )
    parser.add_argument("--write", action="store_true", help="write the notes")
    parser.add_argument("--source", default=None, help="only this source's files")
    parser.add_argument("--limit", type=int, default=None, help="at most this many files")
    args = parser.parse_args(argv)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("not started: DATABASE_URL is not set", file=sys.stderr)
        return 2
    try:
        store = archive_from_env()
    except NotConfigured as exc:
        print(f"not started: {exc}", file=sys.stderr)
        return 2

    def progress(summary: RereadSummary) -> None:
        if summary.documents % 100 == 0:
            print(f"{summary.documents} files, {summary.read_again} read again", file=sys.stderr)

    with psycopg.connect(database_url, autocommit=True) as conn:
        summary = reread(
            conn, store, write=args.write, source=args.source, limit=args.limit, progress=progress
        )
    print(json.dumps(dataclasses.asdict(summary), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
