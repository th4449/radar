"""Text extraction and the hash-named archive."""

from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path

import pytest

from collectors.base import FetchResult, LocalArchive, archive, sha256_hex
from pipeline.extract import extract, sniff

from .helpers import make_pdf, make_source

SYNTHETIC = Path(__file__).parent / "fixtures" / "synthetic"


def result_for(body: bytes, content_type: str | None, url="https://records.example.gov/doc"):
    now = dt.datetime(2026, 11, 19, 12, 0, tzinfo=dt.UTC)
    return FetchResult(url, url, 200, content_type, '"e1"', None, body, now)


# --- extraction ---------------------------------------------------------------------------------


def test_html_text_keeps_the_notice_and_drops_scripts_and_styles():
    out = extract((SYNTHETIC / "notice.html").read_bytes(), "text/html; charset=utf-8")
    assert out.kind == "html"
    assert out.title == "Notice of Public Hearing"
    assert "Project Falcon LLC" in out.text
    assert "reinvestment zone" in out.text
    assert "640 acres" in out.text
    assert "tracking" not in out.text  # script body
    assert "font-family" not in out.text  # style body
    assert "\n\n" not in out.text and "  " not in out.text


def test_pdf_text_is_extracted_page_by_page():
    body = make_pdf(["Permit application 177301\nApplicant: Example Power LLC", "Page two: 240 MW"])
    out = extract(body, "application/pdf")
    assert (out.kind, out.pages, out.needs_ocr) == ("pdf", 2, False)
    assert "Applicant: Example Power LLC" in out.text
    assert "240 MW" in out.text


def test_a_pdf_with_no_text_layer_is_flagged_for_ocr():
    out = extract(make_pdf(["", ""]), "application/pdf")
    assert (out.kind, out.pages, out.text, out.needs_ocr) == ("pdf", 2, "", True)


@pytest.mark.parametrize(
    "body,content_type,kind",
    [
        (b"%PDF-1.7\n...", "text/html", "pdf"),  # mislabeled by the server
        (b"<!DOCTYPE html><html></html>", "application/octet-stream", "html"),
        (b"  <html><body>x</body></html>", None, "html"),
        (b'{"a": 1}', "application/json", "text"),
        (b"plain words", None, "text"),
        (b"\x00\x01\x02\xff", None, "unknown"),
        (b"<html>login page</html>", "application/pdf", "html"),  # a PDF link that served HTML
    ],
)
def test_kind_is_decided_from_the_bytes(body, content_type, kind):
    assert sniff(body, content_type) == kind


def test_unknown_bytes_give_empty_text():
    assert extract(b"\x00\x01\x02\xff").text == ""


# --- archive ------------------------------------------------------------------------------------


def test_archive_stores_the_original_under_its_hash(tmp_path):
    body = (SYNTHETIC / "notice.html").read_bytes()
    store = LocalArchive(tmp_path)
    doc = archive(result_for(body, "text/html"), make_source(), store)

    digest = hashlib.sha256(body).hexdigest()
    assert doc.sha256 == digest
    assert doc.storage_path == f"{digest[:2]}/{digest}.html"
    assert store.get(doc.storage_path) == body  # byte for byte
    assert doc.source_id == "tx_example"
    assert doc.url == "https://records.example.gov/doc"
    assert doc.retrieved_at == dt.datetime(2026, 11, 19, 12, 0, tzinfo=dt.UTC)
    assert "Project Falcon LLC" in doc.text
    assert doc.raw_meta["kind"] == "html"
    assert doc.raw_meta["bytes"] == len(body)
    assert doc.raw_meta["etag"] == '"e1"'


def test_archiving_the_same_bytes_twice_keeps_one_file(tmp_path):
    body = make_pdf(["Same document"])
    store = LocalArchive(tmp_path)
    first = archive(result_for(body, "application/pdf"), make_source(), store)
    second = archive(result_for(body, "application/pdf"), make_source(), store)
    assert first.storage_path == second.storage_path
    assert first.storage_path.endswith(".pdf")
    assert len([p for p in tmp_path.rglob("*") if p.is_file()]) == 1


def test_archive_refuses_a_hash_that_does_not_match(tmp_path):
    with pytest.raises(ValueError):
        LocalArchive(tmp_path).put(sha256_hex(b"other"), b"body", "bin")
