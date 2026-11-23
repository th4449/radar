"""A page saved by hand, stored in the database the way a run stores one."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from collectors import by_hand
from collectors.base import LocalArchive
from pipeline import process
from pipeline.config import load_sources
from pipeline.store import PostgresSink

from .conftest import as_service

pytestmark = pytest.mark.db

PAGE = Path(__file__).parent.parent / "fixtures/tx_comptroller_data_centers/data-center-lists.html"
SAVED_AT = dt.datetime(2026, 11, 24, 15, 30, tzinfo=dt.UTC)


def test_the_rules_read_the_list_a_person_saved(db, tmp_path):
    store = LocalArchive(tmp_path)
    with as_service(db):
        assert process.load_rules(db, store).listings == {}
        summary = by_hand.store_saved_page(
            source=load_sources().by_id("tx_comptroller_data_centers"),
            path=PAGE,
            saved_at=SAVED_AT,
            store=store,
            sink=PostgresSink(db),
            now=SAVED_AT + dt.timedelta(minutes=5),
        )
        rules = process.load_rules(db, store)
    assert (summary.status, summary.documents_new) == ("ok", 1)
    assert "AMAZON DATA SERVICES INC" in rules.listings
    retrieved_at, by_hand_flag, restricted = db.execute(
        "select retrieved_at, raw_meta->>'by_hand', restricted from public.documents"
    ).fetchone()
    assert (retrieved_at, by_hand_flag, restricted) == (SAVED_AT, "true", False)
    runner, status, new = db.execute(
        "select runner, status, documents_new from public.collector_runs"
    ).fetchone()
    assert (runner, status, new) == ("by-hand", "ok", 1)


def test_the_backtest_reads_the_newest_list_the_history_holds(db, tmp_path):
    from backtest.run import stored_listing

    store = LocalArchive(tmp_path)
    with as_service(db):
        assert stored_listing(db, store) is None
        by_hand.store_saved_page(
            source=load_sources().by_id("tx_comptroller_data_centers"),
            path=PAGE,
            saved_at=SAVED_AT,
            store=store,
            sink=PostgresSink(db),
            now=SAVED_AT + dt.timedelta(minutes=5),
        )
        assert stored_listing(db, store) == PAGE.read_bytes()
