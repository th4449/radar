"""Processing against the database: documents in, signals and entities out."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import psycopg
import pytest

from collectors.base import FetchResult, LocalArchive, archive
from collectors.tx import comptroller_data_centers as comptroller
from collectors.tx import tceq_air_pending_legacy as tceq
from collectors.tx import twdb_well_reports as twdb
from pipeline import process
from pipeline.config import load_counties, load_sources
from pipeline.store import PostgresSink

from ..helpers import make_pdf
from .conftest import as_service, as_user, make_reviewer

pytestmark = pytest.mark.db

FIXTURES = Path(__file__).parent.parent / "fixtures"
LIST = (FIXTURES / "tx_comptroller_data_centers" / "data-center-lists.html").read_bytes()
NSR = (FIXTURES / "tx_tceq_air_pending_legacy" / "nsr-pending-permits.html").read_bytes()
WELLS = (FIXTURES / "tx_twdb_well_reports" / "welldata-sample.txt").read_bytes()
RPG_URL = "https://www.ercot.com/files/docs/2026/07/17/6.-Status-Update_July2026_RPG.pdf"
RPG = make_pdf(["Example Cooperative\nHood County Large Load Project", "A 300 MW large load."])

SOURCES = load_sources()
DAY = dt.datetime(2026, 11, 20, 12, 0, tzinfo=dt.UTC)


def well_extract() -> bytes:
    names = frozenset(c.name for c in load_counties("TX").counties)
    lines = WELLS.decode(twdb.ENCODING).split("\r\n")
    return twdb.reduce_table(lines, names, dt.date(2024, 11, 20)).body()


class Stored:
    """A database and an archive folder with documents put in the way a collector does."""

    def __init__(self, conn: psycopg.Connection, root: Path) -> None:
        self.conn, self.store, self.sink = conn, LocalArchive(root), PostgresSink(conn)

    def add(self, source_id: str, url: str, body: bytes, content_type: str, day: int = 0) -> int:
        source = SOURCES.by_id(source_id)
        when = DAY + dt.timedelta(days=day)
        result = FetchResult(url, url, 200, content_type, None, None, body, when)
        with as_service(self.conn):
            self.sink.start_run(source)
            doc = archive(result, source, self.store)
            assert self.sink.save_document(doc)
        return self.conn.execute(
            "select id from public.documents where sha256 = %s", [doc.sha256]
        ).fetchone()[0]

    def add_everything(self) -> dict[str, int]:
        return {
            "list": self.add("tx_comptroller_data_centers", comptroller.URL, LIST, "text/html"),
            "nsr": self.add("tx_tceq_air_pending_legacy", tceq.NSR, NSR, "text/html"),
            "wells": self.add("tx_twdb_well_reports", twdb.URL, well_extract(), "text/plain"),
            "rpg": self.add("tx_ercot_rpg", RPG_URL, RPG, "application/pdf"),
        }

    def run(self, **kwargs) -> process.ProcessSummary:
        with as_service(self.conn):
            return process.run(self.conn, self.store, **kwargs)

    def signals(self, where: str = "true", params: list | None = None) -> list[tuple]:
        return self.conn.execute(
            f"""select sg.signal_type, sg.document_id, sg.county_fips, sg.summary, e.normalized_name
                from public.signals sg left join public.entities e on e.id = sg.entity_id
                where sg.fingerprint is not null and {where}
                order by sg.signal_type, sg.summary""",
            params,
        ).fetchall()


@pytest.fixture
def stored(db, tmp_path) -> Stored:
    return Stored(db, tmp_path)


def test_documents_become_signals_with_their_companies(stored):
    ids = stored.add_everything()
    summary = stored.run(runner="test")

    assert summary.status == "ok" and summary.errors == 0
    assert summary.documents == 3  # the Comptroller's list is consulted, not read for signals
    assert summary.signals_new == 6 + 3 + 1
    by_type = {}
    for signal_type, document_id, *_ in stored.signals():
        by_type.setdefault(signal_type, set()).add(document_id)
    assert by_type == {
        "air_permit": {ids["nsr"]},
        "well_report": {ids["wells"]},
        "transmission_filing": {ids["rpg"]},
    }
    companies = {row[4] for row in stored.signals("sg.signal_type = 'air_permit'")}
    assert "ALIGNED DATA CENTERS REIT LLC" in companies and None not in companies
    # A planning file names utilities, so no company is attached to its signal.
    assert stored.signals("sg.signal_type = 'transmission_filing'")[0][4] is None


def test_a_run_is_logged_with_counts_for_each_source(stored):
    stored.add_everything()
    summary = stored.run(runner="test")
    row = stored.conn.execute(
        """select status, rules_version, documents, signals_new, held_back, errors, runner,
                  finished_at is not null, detail
           from public.processing_runs order by id desc limit 1"""
    ).fetchone()
    assert row[:8] == ("ok", summary.rules_version, 3, 10, 0, 0, "test", True)
    assert row[8]["by_source"]["tx_tceq_air_pending_legacy"] == {
        "documents": 1, "new": 6, "records": 296, "signals": 6, "no_reason": 290,
        "held_back": 0, "out_of_scope": 0, "undated": 0,
    }  # fmt: skip


def test_each_document_is_marked_and_a_second_run_reads_nothing(stored):
    ids = stored.add_everything()
    first = stored.run()
    marked = dict(
        stored.conn.execute(
            "select id, processed_version from public.documents where id = any(%s)",
            [list(ids.values())],
        ).fetchall()
    )
    assert marked[ids["nsr"]] == marked[ids["wells"]] == marked[ids["rpg"]] == first.rules_version
    assert marked[ids["list"]] is None
    again = stored.run()
    assert (again.status, again.documents, again.signals_new) == ("ok", 0, 0)


def test_a_file_about_one_county_marks_its_document(stored):
    ids = stored.add_everything()
    stored.run()
    assert stored.conn.execute(
        "select county_fips from public.documents where id = %s", [ids["rpg"]]
    ).fetchone() == ("48221",)
    assert stored.signals("sg.signal_type = 'transmission_filing'")[0][2] == "48221"


def test_the_same_row_in_a_later_copy_of_a_list_makes_no_second_signal(stored):
    ids = stored.add_everything()
    stored.run()
    later = stored.add(
        "tx_tceq_air_pending_legacy", tceq.NSR, NSR + b"<!-- rebuilt -->", "text/html", day=7
    )
    summary = stored.run()
    assert (summary.documents, summary.signals_new) == (1, 0)
    owners = {row[1] for row in stored.signals("sg.signal_type = 'air_permit'")}
    assert owners == {ids["nsr"]} and later not in owners


def test_a_new_row_in_a_later_copy_belongs_to_that_copy(stored):
    stored.add_everything()
    stored.run()
    changed = NSR.replace(b"ADC PLANO", b"ADC PLANO DATA CENTER").replace(b"131651", b"999001")
    assert changed != NSR
    later = stored.add("tx_tceq_air_pending_legacy", tceq.NSR, changed, "text/html", day=7)
    summary = stored.run()
    assert summary.signals_new == 1
    ((_, document_id, _, text, _),) = stored.signals("sg.summary like %s", ["%permit 999001%"])
    assert document_id == later and "ADC PLANO DATA CENTER" in text


def test_a_record_that_may_name_a_person_leaves_no_trace_of_the_name(stored):
    stored.add("tx_comptroller_data_centers", comptroller.URL, LIST, "text/html")
    body = NSR.replace(b"CRUSOE ENERGY SYSTEMS LLC", b"INVENTED PERSON")
    stored.add("tx_tceq_air_pending_legacy", tceq.NSR, body, "text/html")
    summary = stored.run()
    assert summary.held_back == 2 and summary.signals_new == 4
    assert summary.detail["held_refs"] == [
        "TCEQ New Source Review permit 182126, GHGPSDTX263, PSDTX1688",
        "TCEQ New Source Review permit 182880, GHGPSDTX268, PSDTX1698",
    ]
    leaked = stored.conn.execute(
        """select (select count(*) from public.signals where summary like '%INVENTED%'
                      or extracted::text like '%INVENTED%')
                + (select count(*) from public.entities where name like '%INVENTED%')
                + (select count(*) from public.processing_runs where detail::text like '%INVENTED%'
                      or error like '%INVENTED%')"""
    ).fetchone()[0]
    assert leaked == 0


def test_a_document_that_cannot_be_read_is_left_for_the_next_run(stored):
    stored.add("tx_comptroller_data_centers", comptroller.URL, LIST, "text/html")
    broken = stored.add(
        "tx_tceq_air_pending_legacy", tceq.NSR, b"<html>maintenance</html>", "text/html"
    )
    stored.add("tx_twdb_well_reports", twdb.URL, well_extract(), "text/plain")
    summary = stored.run()
    assert (summary.status, summary.errors, summary.documents) == ("partial", 1, 1)
    assert summary.signals_new == 3
    assert summary.detail["errors"][0]["document_id"] == broken
    assert stored.conn.execute(
        "select processed_version from public.documents where id = %s", [broken]
    ).fetchone() == (None,)


def test_a_file_missing_from_the_archive_is_an_error_not_a_crash(stored):
    ids = stored.add_everything()
    path = stored.conn.execute(
        "select storage_path from public.documents where id = %s", [ids["rpg"]]
    ).fetchone()[0]
    (stored.store.root / path).unlink()
    summary = stored.run()
    assert (summary.status, summary.errors, summary.documents) == ("partial", 1, 2)


def test_a_new_copy_of_the_comptroller_list_makes_every_document_be_read_again(stored):
    stored.add_everything()
    first = stored.run()
    # The list is one of the things the rules consult, so a new copy is a new set of rules.
    stored.add(
        "tx_comptroller_data_centers", comptroller.URL, LIST + b"<!-- updated -->", "text/html",
        day=30,
    )  # fmt: skip
    second = stored.run()
    assert second.rules_version != first.rules_version
    assert second.documents == 3
    assert second.signals_new == 0  # reading again never stores a fact twice
    assert len(stored.signals()) == 10


def test_without_the_comptroller_list_only_the_words_count(stored):
    stored.add("tx_tceq_air_pending_legacy", tceq.NSR, NSR, "text/html")
    summary = stored.run()
    assert summary.signals_new == 4
    assert "Comptroller" in summary.detail["note"]


def test_a_limit_reads_the_oldest_documents_first(stored):
    ids = stored.add_everything()
    older = stored.add(
        "tx_tceq_air_pending_legacy", tceq.NSR, NSR + b"<!-- older -->", "text/html", day=-7
    )
    summary = stored.run(limit=1)
    assert summary.documents == 1
    assert {row[1] for row in stored.signals()} == {older}
    assert ids["nsr"] not in {row[1] for row in stored.signals()}


def test_a_reviewer_sees_the_signal_and_not_the_list_it_came_from(stored):
    ids = stored.add_everything()
    stored.run()
    reviewer = make_reviewer(stored.conn)
    with as_user(stored.conn, reviewer):
        seen = stored.conn.execute(
            "select count(*) from public.signals where document_id = %s", [ids["nsr"]]
        ).fetchone()[0]
        lists = stored.conn.execute(
            "select count(*) from public.documents where id = any(%s)",
            [[ids["nsr"], ids["wells"]]],
        ).fetchone()[0]
        open_docs = stored.conn.execute(
            "select count(*) from public.documents where id = any(%s)",
            [[ids["rpg"], ids["list"]]],
        ).fetchone()[0]
    assert (seen, lists, open_docs) == (6, 0, 2)


def test_every_stored_signal_says_which_rules_made_it(stored):
    stored.add_everything()
    summary = stored.run()
    versions = stored.conn.execute(
        "select distinct extracted->>'rules_version' from public.signals"
        " where fingerprint is not null"
    ).fetchall()
    assert versions == [(summary.rules_version,)]
