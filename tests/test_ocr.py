"""Scanned PDFs are read by Tesseract, on this machine, and the result says so.

The scans here are made up: typed lines drawn as a picture, with no text in the file. A real
scanned agenda names people. How Tesseract did on 28 real ones is in docs/services/tesseract.md.

The tests that need Tesseract are skipped where it is not installed. In CI it is installed and
RADAR_REQUIRE_OCR makes a skip a failure.
"""

from __future__ import annotations

import datetime as dt
import os

import pytest

from collectors.base import FetchResult, LocalArchive, archive
from pipeline import extract as extract_module
from pipeline import ocr
from pipeline.extract import extract

from .helpers import make_pdf, make_scan, make_source

REQUIRE = os.environ.get("RADAR_REQUIRE_OCR") == "1"
HEAD = "CITY OF EXAMPLE\nNOTICE OF MEETING AND AGENDA\nTuesday, November 17, 2026 at 6:00 p.m."
ITEMS = (
    "1. Call to order.\n"
    "2. Public hearing on designating a reinvestment zone.\n"
    "3. Presentation on a proposed data center and its water use."
)

needs_tesseract = pytest.mark.skipif(
    not ocr.available() and not REQUIRE, reason="Tesseract is not installed"
)


def test_tesseract_is_installed_where_it_is_required():
    if REQUIRE:
        assert ocr.available(), "RADAR_REQUIRE_OCR is set and Tesseract is not installed"
        assert ocr.engine().startswith("tesseract ")


# --- reading Tesseract's table: no program needed -------------------------------------------------

TSV = (
    "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
    "1\t1\t0\t0\t0\t0\t0\t0\t2550\t3300\t-1\t\n"
    "4\t1\t1\t1\t1\t0\t240\t260\t900\t50\t-1\t\n"
    "5\t1\t1\t1\t1\t1\t240\t260\t300\t50\t96.5\tNOTICE\n"
    "5\t1\t1\t1\t1\t2\t560\t260\t60\t50\t95.0\tOF\n"
    "5\t1\t1\t1\t1\t3\t640\t260\t300\t50\t91.5\tMEETING\n"
    '5\t1\t1\t1\t2\t1\t240\t340\t200\t50\t41.0\t"Agenda\n'
    "5\t1\t1\t1\t2\t2\t460\t340\t20\t50\t30.0\t \n"
    "5\t1\t2\t1\t1\t1\t240\t600\t200\t50\t88.0\tAdjourn\n"
)


def test_words_are_joined_into_the_lines_tesseract_saw():
    text, scores = ocr.read_tsv(TSV)
    assert text == 'NOTICE OF MEETING\n"Agenda\nAdjourn'
    # A quotation mark in a word is a character, not the start of a quoted field. An empty
    # word and the rows for pages and lines are not words.
    assert scores == [96.5, 95.0, 91.5, 41.0, 88.0]


def test_a_table_with_no_words_is_an_empty_page():
    assert ocr.read_tsv(TSV.splitlines()[0] + "\n") == ("", [])
    assert ocr.read_tsv("") == ("", [])


def test_without_tesseract_a_scan_stays_unread_and_nothing_fails(monkeypatch):
    monkeypatch.setattr(ocr, "engine", lambda: None)
    assert not ocr.available()
    with pytest.raises(ocr.OcrFailed, match="not installed"):
        ocr.read_pdf(make_scan([HEAD]))
    out = extract(make_scan([HEAD]))
    assert (out.kind, out.pages, out.text, out.needs_ocr, out.ocr) == ("pdf", 1, "", True, None)


def test_a_failure_of_the_program_leaves_the_scan_unread(monkeypatch):
    def broken(body, max_pages=ocr.MAX_PAGES):
        raise ocr.OcrFailed("TimeoutExpired")

    monkeypatch.setattr(ocr, "engine", lambda: "tesseract 0.0")
    monkeypatch.setattr(ocr, "read_pdf", broken)
    out = extract(make_scan([HEAD]))
    assert (out.text, out.needs_ocr, out.ocr) == ("", True, None)


def test_a_scan_whose_pages_the_text_reader_cannot_find_is_still_counted_as_a_scan(monkeypatch):
    """A real county agenda gave the text reader no pages at all. The page drawer found two."""
    monkeypatch.setattr(ocr, "engine", lambda: None)
    monkeypatch.setattr(extract_module, "_pdf_pages", lambda body: [])
    out = extract(make_scan([HEAD, ITEMS]))
    assert (out.pages, out.text, out.needs_ocr) == (2, "", True)
    # A file neither can open has no pages and is not called a scan.
    monkeypatch.setattr(extract_module, "_page_count", lambda body: 0)
    out = extract(make_scan([HEAD]))
    assert (out.pages, out.needs_ocr) == (0, False)


def test_a_pdf_that_has_text_is_never_sent_to_tesseract(monkeypatch):
    def never(body):
        raise AssertionError("a file with a text layer was sent to OCR")

    monkeypatch.setattr(extract_module, "_scan", never)
    out = extract(make_pdf(["AGENDA", "Consider a tax abatement agreement."]))
    assert "tax abatement" in out.text and out.ocr is None and not out.needs_ocr


# --- with Tesseract -------------------------------------------------------------------------------


@needs_tesseract
def test_a_scan_is_read_page_by_page():
    read = ocr.read_pdf(make_scan([HEAD, ITEMS]))
    assert (len(read.pages), read.pages_in_file) == (2, 2)
    assert "NOTICE OF MEETING AND AGENDA" in read.pages[0]
    assert "November 17, 2026" in read.pages[0]
    assert "reinvestment zone" in read.pages[1] and "data center" in read.pages[1]
    assert read.engine.startswith("tesseract ")
    assert read.words > 30 and read.confidence > 80
    assert read.doubtful_words < read.words / 10


@needs_tesseract
def test_only_the_first_pages_of_a_long_scan_are_read_and_the_count_says_so():
    read = ocr.read_pdf(make_scan([HEAD, ITEMS, ITEMS]), max_pages=2)
    assert (len(read.pages), read.pages_in_file) == (2, 3)
    assert read.facts()["pages_read"] == 2 and read.facts()["pages_in_file"] == 3


@needs_tesseract
def test_the_extractor_reads_a_scan_and_says_the_text_is_a_machines_reading():
    out = extract(make_scan([HEAD, ITEMS]))
    assert (out.kind, out.pages, out.needs_ocr) == ("pdf", 2, False)
    assert "reinvestment zone" in out.text
    # One passage a page, as for a file with a text layer: a blank line between pages only.
    assert out.text.count("\n\n") == 1
    assert out.ocr["engine"].startswith("tesseract ")
    assert out.ocr["dpi"] == 300 and out.ocr["pages_read"] == 2
    assert out.ocr["confidence"] > 80 and out.ocr["words"] > 30


@needs_tesseract
def test_a_scan_whose_pages_the_text_reader_cannot_find_is_read_all_the_same(monkeypatch):
    monkeypatch.setattr(extract_module, "_pdf_pages", lambda body: [])
    out = extract(make_scan([HEAD, ITEMS]))
    assert (out.pages, out.needs_ocr) == (2, False)
    assert "reinvestment zone" in out.text and out.ocr["pages_read"] == 2


@needs_tesseract
def test_a_scan_of_blank_pages_is_still_unread():
    out = extract(make_scan(["", ""]))
    assert (out.pages, out.text, out.needs_ocr, out.ocr) == (2, "", True, None)


@needs_tesseract
def test_a_scans_pages_with_no_words_are_noted_too():
    # The second page is blank. The text has two pieces, and they are pages 1 and 3.
    out = extract(make_scan([HEAD, "", ITEMS]))
    assert (out.pages, out.text.count("\n\n")) == (3, 1)
    assert out.blank_pages == (2,)
    assert extract(make_scan([HEAD, ITEMS])).blank_pages == ()
    # A scan that could not be read has no text to match to pages, and no note.
    assert extract(make_scan(["", ""])).blank_pages is None


@needs_tesseract
def test_what_is_stored_with_a_scan_says_where_its_text_came_from(tmp_path):
    body = make_scan([HEAD, ITEMS])
    result = FetchResult(
        url="https://www.example.gov/files/agenda.pdf",
        final_url="https://www.example.gov/files/agenda.pdf",
        status=200,
        content_type="application/pdf",
        body=body,
        retrieved_at=dt.datetime(2026, 11, 21, 20, 0, tzinfo=dt.UTC),
        etag=None,
        last_modified=None,
    )
    doc = archive(result, make_source(), LocalArchive(tmp_path))
    assert doc.raw_meta["needs_ocr"] is False
    assert doc.raw_meta["ocr"]["engine"].startswith("tesseract ")
    assert "data center" in doc.text
    # The scan itself is what is kept. The text is a reading of it.
    assert LocalArchive(tmp_path).get(doc.storage_path) == body
