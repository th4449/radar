"""A record entered by hand, stored in the database."""

from __future__ import annotations

import datetime as dt

import pytest

from collectors.base import LocalArchive
from pipeline import hand_entry
from pipeline.signals import Rules

from ..test_hand_entry import NOTICES, NOW, SAVED_AT, facts, saved
from .conftest import as_service

pytestmark = pytest.mark.db


def enter(db, tmp_path, **changes):
    path = changes.pop("path", None) or saved(tmp_path)
    with as_service(db):
        return hand_entry.enter(
            db,
            LocalArchive(tmp_path / "archive"),
            NOTICES,
            path,
            facts(**changes),
            saved_at=SAVED_AT,
            now=NOW,
            rules=Rules(listings={}),
        )


def test_the_file_is_stored_with_its_hash_and_the_signal_lands_on_a_site(db, tmp_path):
    made = enter(db, tmp_path)
    assert (made["document_new"], made["signal_new"]) == (True, True)
    url, retrieved_at, by_hand, storage_path, sha = db.execute(
        "select url, retrieved_at, raw_meta->>'by_hand', storage_path, sha256 from public.documents"
    ).fetchone()
    assert url == "https://www.notices.example.gov/notice/4471"
    assert (retrieved_at, by_hand) == (SAVED_AT, "true")
    assert LocalArchive(tmp_path / "archive").get(storage_path).startswith(b"%PDF")
    assert storage_path == f"{sha[:2]}/{sha}.pdf"

    kind, day, county, confidence, entity, site, reference = db.execute(
        """select sg.signal_type, sg.event_date, sg.county_fips, sg.confidence, e.name,
                  s.label, sg.extracted->>'reference'
           from public.signals sg
           left join public.entities e on e.id = sg.entity_id
           left join public.sites s on s.id = sg.site_id"""
    ).fetchone()
    assert (kind, day, county) == ("abatement_notice", dt.date(2026, 11, 28), "48221")
    assert float(confidence) == 0.9
    assert entity == "Example Hosting LLC"
    assert site == "Example Hosting LLC, Hood County" == made["site"]
    assert reference == "Example county notices, Notice 4471"


def test_a_tax_abatement_notice_that_says_data_center_reaches_a_reviewer(db, tmp_path):
    enter(db, tmp_path)
    status, score = db.execute("select status, score from public.sites").fetchone()
    assert status == "in_review" and float(score) > 20


def test_the_same_record_entered_twice_is_one_signal(db, tmp_path):
    enter(db, tmp_path)
    again = enter(db, tmp_path)
    assert (again["document_new"], again["signal_new"]) == (False, False)
    assert db.execute("select count(*) from public.signals").fetchone() == (1,)
    assert db.execute("select count(*) from public.sites").fetchone() == (1,)


def test_the_entry_is_logged_as_made_by_hand(db, tmp_path):
    enter(db, tmp_path)
    runner, status, new = db.execute(
        "select runner, status, documents_new from public.collector_runs"
    ).fetchone()
    assert (runner, status, new) == ("by-hand", "ok", 1)
