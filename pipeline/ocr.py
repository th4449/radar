"""Reading the text of a scanned PDF with Tesseract, on this machine.

Most small governments post their agendas as scans: pictures of paper, with no text in the
file. This module turns each page into a picture and asks Tesseract what it says. Tesseract is
free software under the Apache 2.0 license. It runs here. Nothing is sent to any service.

The text it gives is a machine's reading, not the record. So everything read this way is marked:
the stored document says the text came from OCR, with which engine and how sure it was, and a
signal made from it says so too. A reviewer opens the scan itself.

Tesseract is a program, not a Python package. Where it is not installed, `available()` is
false, a scan stays unread and is counted as unread, as before. Nothing fails.

What it does well and badly, measured on 28 real agendas on November 21, 2026, is in
docs/services/tesseract.md. Running text reads well. Tables come out jumbled.
"""

from __future__ import annotations

import csv
import functools
import io
import shutil
import subprocess
from dataclasses import dataclass

import pypdfium2 as pdfium

PROGRAM = "tesseract"
DPI = 300  # what Tesseract's own guidance asks for
MAX_SIDE = 4200  # pixels. A plan sheet at 300 dots an inch would be a hundred times a letter page
MAX_PAGES = 150  # a longer scan is a packet. Its first pages hold the agenda
PAGE_TIMEOUT = 120  # seconds
LOW = 60  # Tesseract's own score, 0 to 100, under which a word is doubtful


@dataclass(frozen=True)
class OcrResult:
    pages: tuple[str, ...]  # the text of each page that was read, in order. "" where none
    pages_in_file: int
    words: int
    confidence: float | None  # the mean of Tesseract's score for each word. None with no words
    doubtful_words: int  # words scored under LOW
    engine: str  # such as "tesseract 5.5.4"

    @property
    def text(self) -> str:
        return "\n\n".join(page for page in self.pages if page)

    def facts(self) -> dict:
        """What is stored with the document, so a reader knows where its text came from."""
        return {
            "engine": self.engine,
            "dpi": DPI,
            "pages_read": len(self.pages),
            "pages_in_file": self.pages_in_file,
            "words": self.words,
            "confidence": self.confidence,
            "doubtful_words": self.doubtful_words,
        }


class OcrFailed(Exception):
    """Tesseract could not be run on a page, or gave nothing that could be read."""


@functools.cache
def engine() -> str | None:
    """The installed Tesseract and its version, or None when it is not installed."""
    if shutil.which(PROGRAM) is None:
        return None
    try:
        # The arguments are fixed. Nothing from a fetched file reaches the command line.
        out = subprocess.run(  # noqa: S603
            [PROGRAM, "--version"], capture_output=True, timeout=20, check=True
        )
    except (OSError, subprocess.SubprocessError):
        return None
    first = (out.stdout or out.stderr).decode("utf-8", "replace").splitlines()[:1]
    return first[0].strip() if first else None


def available() -> bool:
    return engine() is not None


def read_tsv(tsv: str) -> tuple[str, list[float]]:
    """A page's text and each word's score, from Tesseract's table of what it found.

    Words are joined into the lines Tesseract saw them on, and lines are kept in its order.
    """
    lines: dict[tuple[str, str, str, str], list[str]] = {}
    scores: list[float] = []
    for row in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE):
        word = (row.get("text") or "").strip()
        if row.get("level") != "5" or not word:
            continue  # level 5 is a word. The other rows are pages, blocks and lines
        try:
            score = float(row["conf"])
        except (KeyError, TypeError, ValueError):
            continue
        key = (row["page_num"], row["block_num"], row["par_num"], row["line_num"])
        lines.setdefault(key, []).append(word)
        scores.append(score)
    return "\n".join(" ".join(words) for words in lines.values()), scores


def _scale(page: pdfium.PdfPage) -> float:
    width, height = page.get_size()  # in points, 72 to the inch
    return min(DPI / 72, MAX_SIDE / max(width, height, 1))


def _read_page(page: pdfium.PdfPage) -> tuple[str, list[float]]:
    image = page.render(scale=_scale(page), grayscale=True).to_pil()
    png = io.BytesIO()
    image.save(png, format="PNG")
    command = [PROGRAM, "stdin", "stdout", "-l", "eng", "--psm", "3", "--dpi", str(DPI), "tsv"]
    try:
        # The arguments are fixed. The page goes in as a picture this code drew, on stdin.
        done = subprocess.run(  # noqa: S603
            command, input=png.getvalue(), capture_output=True, timeout=PAGE_TIMEOUT, check=True
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise OcrFailed(f"{type(exc).__name__}") from exc
    return read_tsv(done.stdout.decode("utf-8", "replace"))


def read_pdf(body: bytes, max_pages: int = MAX_PAGES) -> OcrResult:
    """The text Tesseract reads from each page of a PDF, the first max_pages at most.

    Raises OcrFailed when Tesseract is not installed or cannot be run. A page it reads nothing
    from is an empty page, not a failure.
    """
    name = engine()
    if name is None:
        raise OcrFailed("Tesseract is not installed")
    try:
        document = pdfium.PdfDocument(body)
    except pdfium.PdfiumError as exc:
        raise OcrFailed("the file could not be opened") from exc
    try:
        count = len(document)
        pages: list[str] = []
        scores: list[float] = []
        for index in range(min(count, max_pages)):
            page = document[index]
            try:
                text, found = _read_page(page)
            finally:
                page.close()
            pages.append(text)
            scores += found
    finally:
        document.close()
    return OcrResult(
        pages=tuple(pages),
        pages_in_file=count,
        words=len(scores),
        confidence=round(sum(scores) / len(scores), 1) if scores else None,
        doubtful_words=sum(1 for score in scores if score < LOW),
        engine=name,
    )
