"""The command that stores a page a person saved in a browser. Written before the command.

A site can refuse the radar's reader and still be a public page a person may open and save. The
command takes that saved file. It makes no request, checks the file is the page it is said to
be, and stores it the way a run stores a page, marked as saved by hand.
"""

from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path

import httpx
import pytest

from collectors import by_hand
from collectors.base import LocalArchive
from collectors.tx.comptroller_data_centers import URL, parse
from pipeline.config import load_sources
from pipeline.store import MemorySink

from .test_tx_comptroller_data_centers import BODY

SAVED_AT = dt.datetime(2026, 11, 24, 15, 30, tzinfo=dt.UTC)
NOW = dt.datetime(2026, 11, 24, 16, 0, tzinfo=dt.UTC)


def lists():
    return load_sources().by_id("tx_comptroller_data_centers")


def saved(tmp_path: Path, body: bytes = BODY, name: str = "data-center-lists.html") -> Path:
    path = tmp_path / "downloads" / name
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(body)
    return path


def store_it(tmp_path: Path, sink: MemorySink, **changes):
    values = {
        "source": lists(),
        "path": saved(tmp_path),
        "saved_at": SAVED_AT,
        "store": LocalArchive(tmp_path / "archive"),
        "sink": sink,
        "now": NOW,
    }
    return by_hand.store_saved_page(**{**values, **changes})


def test_a_saved_page_is_stored_with_its_address_its_time_and_its_hash(tmp_path):
    sink = MemorySink()
    summary = store_it(tmp_path, sink)

    assert (summary.status, summary.documents_seen, summary.documents_new) == ("ok", 1, 1)
    (doc,) = sink.documents.values()
    assert doc.url == URL  # the page the collector reads, not the name of the file
    assert doc.retrieved_at == SAVED_AT
    assert doc.sha256 == hashlib.sha256(BODY).hexdigest()
    assert LocalArchive(tmp_path / "archive").get(doc.storage_path) == BODY
    assert "Whinstone US Data Center" in doc.text
    assert parse(LocalArchive(tmp_path / "archive").get(doc.storage_path)) == parse(BODY)


def test_the_record_says_a_person_saved_the_page(tmp_path):
    sink = MemorySink()
    store_it(tmp_path, sink)
    (doc,) = sink.documents.values()
    assert doc.raw_meta["by_hand"] is True
    assert doc.raw_meta["kind"] == "html"
    # The name of the file on a person's own computer is nobody's business.
    assert "data-center-lists.html" not in str(doc.raw_meta)
    (run,) = sink.runs.values()
    assert (run["runner"], run["status"]) == ("by-hand", "ok")


def test_no_request_is_made(tmp_path, monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("the command asked a site for something")

    monkeypatch.setattr(httpx.Client, "send", refuse)
    assert store_it(tmp_path, MemorySink()).status == "ok"


def test_the_same_file_stored_twice_is_one_document(tmp_path):
    sink = MemorySink()
    store_it(tmp_path, sink)
    again = store_it(tmp_path, sink)
    assert (again.status, again.documents_new) == ("ok", 0)
    assert len(sink.documents) == 1


@pytest.mark.parametrize(
    "body",
    [
        b"<html><body><h1>Message Code: CTG-CF-403</h1></body></html>",  # the refusal page
        b"<html><body><main><table></table></main></body></html>",
        b"bplist00\xd1\x01\x02",  # a browser's own archive format, not the page
        b"",
    ],
)
def test_a_file_that_is_not_the_page_is_refused_and_nothing_is_stored(tmp_path, body):
    sink = MemorySink()
    with pytest.raises(by_hand.NotStored, match="not the page"):
        store_it(tmp_path, sink, path=saved(tmp_path, body, "another-file.html"))
    assert sink.documents == {} and sink.runs == {}
    assert not (tmp_path / "archive").exists()


def test_only_a_source_marked_for_it_takes_a_saved_page(tmp_path):
    sink = MemorySink()
    planning = load_sources().by_id("tx_ercot_rpg")  # a job reads it
    with pytest.raises(by_hand.NotStored, match="not marked hand_saved"):
        store_it(tmp_path, sink, source=planning)
    notices = load_sources().by_id("tx_public_notices")  # manual, and its terms bar copies
    with pytest.raises(by_hand.NotStored, match="not marked hand_saved"):
        store_it(tmp_path, sink, source=notices)
    assert sink.documents == {} and sink.runs == {}


def test_a_time_in_the_future_or_with_no_zone_is_refused(tmp_path):
    sink = MemorySink()
    with pytest.raises(by_hand.NotStored, match="in the future"):
        store_it(tmp_path, sink, saved_at=NOW + dt.timedelta(hours=1))
    with pytest.raises(by_hand.NotStored, match="time zone"):
        store_it(tmp_path, sink, saved_at=dt.datetime(2026, 11, 24, 15, 30))
    assert sink.documents == {}


def test_with_no_time_given_the_files_own_time_is_used(tmp_path):
    import os

    path = saved(tmp_path)
    os.utime(path, (SAVED_AT.timestamp(), SAVED_AT.timestamp()))
    assert by_hand.file_time(path) == SAVED_AT


# --- the command line -----------------------------------------------------------------------------


def test_the_command_does_not_start_without_a_database_and_an_archive(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("RADAR_ARCHIVE_DIR", raising=False)
    assert by_hand.main(["tx_comptroller_data_centers", str(saved(tmp_path))]) == 2
    assert "DATABASE_URL" in capsys.readouterr().err


def test_the_command_names_what_is_wrong(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", "postgresql://nowhere.invalid/none")
    monkeypatch.setenv("RADAR_ARCHIVE_DIR", str(tmp_path / "archive"))
    assert by_hand.main(["tx_no_such_source", str(saved(tmp_path))]) == 2
    assert "no source with id" in capsys.readouterr().err
    assert by_hand.main(["tx_comptroller_data_centers", str(tmp_path / "missing.html")]) == 2
    assert "no file" in capsys.readouterr().err
    refusal = saved(tmp_path, b"<html>Message Code: CTG-CF-403</html>", "refused.html")
    assert by_hand.main(["tx_comptroller_data_centers", str(refusal)]) == 1
    assert "not the page" in capsys.readouterr().err
