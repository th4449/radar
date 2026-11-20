"""Text from slide decks, Word files and zip files.

The files here are made by the helpers, so the tests say exactly what is inside each one. The
reader was also run by hand on two real ERCOT files. See docs/sources/tx_ercot_large_load.md.
"""

from __future__ import annotations

import datetime as dt

from collectors.base import FetchResult, LocalArchive, archive
from pipeline import extract as extract_module
from pipeline.extract import extract, sniff

from .helpers import make_docx, make_pdf, make_pptx, make_source, make_zip

PPTX_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


# --- slide decks --------------------------------------------------------------------------------


def test_a_slide_deck_is_read_slide_by_slide():
    deck = make_pptx(["Large Load Queue\n53,546 MW under review", "Next steps\nBatch study"])
    out = extract(deck, PPTX_TYPE)
    assert (out.kind, out.pages, out.needs_ocr) == ("pptx", 2, False)
    assert out.text == "Large Load Queue\n53,546 MW under review\n\nNext steps\nBatch study"


def test_a_slide_deck_is_recognized_whatever_the_server_calls_it():
    deck = make_pptx(["One slide"])
    for content_type in (None, "application/octet-stream", "application/zip", "text/html"):
        assert sniff(deck, content_type) == "pptx"


def test_slides_come_in_presentation_order_not_file_name_order():
    # The first slide shown is stored as slide3.xml, the second as slide1.xml.
    deck = make_pptx(["Shown first", "Shown second", "Shown third"], file_order=[3, 1, 2])
    assert extract(deck).text == "Shown first\n\nShown second\n\nShown third"


def test_speaker_notes_follow_their_slide():
    deck = make_pptx([("Queue update", "Totals are by zone, not by site."), "Questions"])
    assert extract(deck).text == (
        "Queue update\nNotes:\nTotals are by zone, not by site.\n\nQuestions"
    )


def test_the_slide_number_is_left_out():
    out = extract(make_pptx(["First", "Second"]))
    assert "1" not in out.text and "2" not in out.text


def test_a_deck_of_pictures_is_marked_for_character_recognition():
    out = extract(make_pptx(["", ""]))
    assert (out.kind, out.pages, out.text, out.needs_ocr) == ("pptx", 2, "", True)


def test_a_deck_with_a_document_type_declaration_is_kept_and_not_read():
    bad = b'<!DOCTYPE x [<!ENTITY a "aaaa">]><p:sld xmlns:p="p"/>'
    deck = make_zip(
        {
            "[Content_Types].xml": b"<Types/>",
            "ppt/presentation.xml": b"<presentation/>",
            "ppt/slides/slide1.xml": bad,
        }
    )
    out = extract(deck)
    assert (out.kind, out.text) == ("pptx", "")


# --- Word files ---------------------------------------------------------------------------------


def test_a_word_file_is_read_paragraph_by_paragraph():
    out = extract(make_docx(["Agenda", "4. Large Load Issues", "Adjourn"]))
    assert (out.kind, out.text) == ("docx", "Agenda\n4. Large Load Issues\nAdjourn")


# --- zip files ----------------------------------------------------------------------------------


def test_a_zip_file_gives_the_text_of_each_file_inside():
    body = make_zip(
        {
            "10. TAC update.pptx": make_pptx(["Batch study update"]),
            "report/Status.pdf": make_pdf(["Planning studies approved"]),
            "notes.txt": b"Plain notes",
        }
    )
    out = extract(body, "application/zip")
    assert out.kind == "zip"
    assert out.text == (
        "File: 10. TAC update.pptx\nBatch study update\n\n"
        "File: report/Status.pdf\nPlanning studies approved\n\n"
        "File: notes.txt\nPlain notes"
    )
    assert [(m["name"], m["kind"], m["read"]) for m in out.members] == [
        ("10. TAC update.pptx", "pptx", True),
        ("report/Status.pdf", "pdf", True),
        ("notes.txt", "text", True),
    ]
    assert out.members[0]["pages"] == 1


def test_files_a_zip_holds_that_are_not_read_are_listed_with_the_reason():
    workbook = make_zip({"[Content_Types].xml": b"<Types/>", "xl/workbook.xml": b"<workbook/>"})
    body = make_zip(
        {
            "ballot.xlsx": workbook,
            "inner.zip": make_zip({"deep.txt": b"not reached"}),
            "old.ppt": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 64,
            "read.txt": b"This one is read",
        }
    )
    out = extract(body)
    assert out.text == "File: read.txt\nThis one is read"
    unread = {m["name"]: (m["kind"], m["why"]) for m in out.members if not m["read"]}
    assert unread == {
        "ballot.xlsx": ("xlsx", "this kind of file is not read"),
        "inner.zip": ("zip", "this kind of file is not read"),
        "old.ppt": ("unknown", "this kind of file is not read"),
    }


def test_a_scanned_file_inside_a_zip_marks_the_whole_zip():
    out = extract(make_zip({"scan.pdf": make_pdf([""]), "text.txt": b"words"}))
    assert out.needs_ocr


def test_folders_and_hidden_files_in_a_zip_are_skipped():
    body = make_zip({"__MACOSX/._deck.pptx": b"junk", ".DS_Store": b"junk", "a.txt": b"kept"})
    out = extract(body)
    assert [m["name"] for m in out.members] == ["a.txt"]


def test_a_file_that_unpacks_past_the_limit_is_not_read(monkeypatch):
    monkeypatch.setattr(extract_module, "MAX_MEMBER_BYTES", 1000)
    body = make_zip({"big.txt": b"x" * 5000, "small.txt": b"small"})
    out = extract(body)
    assert out.text == "File: small.txt\nsmall"
    assert "unpacks to more than" in out.members[0]["why"]


def test_a_damaged_zip_is_kept_as_an_unknown_file():
    out = extract(b"PK\x03\x04" + b"\x00\x07" * 40)
    assert (out.kind, out.text, out.members) == ("unknown", "", ())


# --- stored under the right name ----------------------------------------------------------------


def result(body: bytes, url: str) -> FetchResult:
    return FetchResult(
        url=url,
        final_url=url,
        status=200,
        content_type="application/octet-stream",
        etag=None,
        last_modified=None,
        body=body,
        retrieved_at=dt.datetime(2026, 11, 20, tzinfo=dt.UTC),
    )


def test_a_deck_and_a_zip_are_stored_with_their_own_file_endings(tmp_path):
    store = LocalArchive(tmp_path)
    deck = archive(result(make_pptx(["Slide text"]), "https://x.example/a"), make_source(), store)
    assert deck.storage_path.endswith(".pptx")
    assert (deck.text, deck.raw_meta["kind"], deck.raw_meta["pages"]) == ("Slide text", "pptx", 1)
    assert "members" not in deck.raw_meta

    zipped = archive(
        result(make_zip({"deck.pptx": make_pptx(["Inside"])}), "https://x.example/b"),
        make_source(),
        store,
    )
    assert zipped.storage_path.endswith(".zip")
    assert zipped.text == "File: deck.pptx\nInside"
    assert zipped.raw_meta["members"][0]["name"] == "deck.pptx"
