"""Sites and scores in the database: signals in, sites out."""

from __future__ import annotations

import datetime as dt
import json

import pytest

from pipeline import process
from pipeline.config import load_scoring
from pipeline.sites import update_sites

from .conftest import as_service, as_user, make_reviewer
from .test_process import Stored

pytestmark = pytest.mark.db

AS_OF = dt.date(2026, 11, 20)
THRESHOLD = load_scoring().thresholds.review_threshold


class Radar(Stored):
    def run(self, as_of: dt.date = AS_OF, **kwargs) -> process.ProcessSummary:
        with as_service(self.conn):
            return process.run(self.conn, self.store, as_of=as_of, **kwargs)

    def sites(self) -> list[tuple]:
        return self.conn.execute(
            """select s.id, s.label, s.county_fips, s.status, s.score,
                      (select count(*) from public.signals sg where sg.site_id = s.id)
               from public.sites s
               order by s.label, s.id"""
        ).fetchall()

    def site(self, label_like: str) -> int:
        return self.conn.execute(
            "select id from public.sites where label like %s", [label_like]
        ).fetchone()[0]

    def add_signal(
        self, site_like: str, signal_type: str, *, days_ago: int = 0, confidence: float = 0.9,
        source: str = "tx_ercot_rpg", point: tuple[float, float] | None = None,
        other_company: str | None = None,
    ) -> int:  # fmt: skip
        """A signal about the same company and county as an existing site, not yet on a site."""
        site_id = self.site(site_like)
        entity_id, county = self.conn.execute(
            """select sg.entity_id, s.county_fips from public.signals sg
               join public.sites s on s.id = sg.site_id where s.id = %s limit 1""",
            [site_id],
        ).fetchone()
        if other_company:
            entity_id = self.conn.execute(
                """insert into public.entities (name, normalized_name, match_key, kind)
                   values (%s, upper(%s), upper(%s), 'company') returning id""",
                [other_company] * 3,
            ).fetchone()[0]
        document_id = self.conn.execute(
            """select d.id from public.documents d join public.sources s on s.id = d.source_id
               where s.slug = %s limit 1""",
            [source],
        ).fetchone()[0]
        extracted = {"point": {"lon": point[0], "lat": point[1]}} if point else {}
        return self.conn.execute(
            """insert into public.signals (document_id, signal_type, event_date, summary,
                                           entity_id, confidence, county_fips, extracted)
               values (%s, %s, %s, 'A later record about the same company.', %s, %s, %s,
                       %s::jsonb)
               returning id""",
            [document_id, signal_type, AS_OF - dt.timedelta(days=days_ago), entity_id,
             confidence, county, json.dumps(extracted)],
        ).fetchone()[0]  # fmt: skip


@pytest.fixture
def radar(db, tmp_path) -> Radar:
    made = Radar(db, tmp_path)
    made.add_everything()
    return made


def test_signals_become_sites_named_for_what_their_first_signal_names(radar):
    summary = radar.run()
    assert [(label, county, status, n) for _, label, county, status, _, n in radar.sites()] == [
        ("CyrusOne Bosque LLC, Bosque County", "48035", "candidate", 1),
        ("NTT Global Data Centers AUI, LLC, Travis County", "48453", "candidate", 2),
    ]
    assert summary.detail["sites"] == {
        "as_of": "2026-11-20", "unplaced": 6, "outside_states": 0, "sites_new": 2,
        "signals_attached": 3, "unanchored": 1, "sites_scored": 2, "moved_to_review": 0,
        "possible_same_site": [], "placeholder_scoring": True,
    }  # fmt: skip


def test_a_signal_with_no_county_is_on_no_site(radar):
    radar.run()
    rows = radar.conn.execute(
        """select signal_type, count(*), count(site_id) from public.signals
           where fingerprint is not null group by 1 order by 1"""
    ).fetchall()
    # The TCEQ lists give no county. The planning file names a county and nothing to hold
    # it to a place within it.
    assert rows == [("air_permit", 6, 0), ("transmission_filing", 1, 0), ("well_report", 3, 3)]


def test_a_site_is_scored_from_its_signals_with_the_breakdown_stored(radar):
    radar.run()
    score, detail, first, scored = radar.conn.execute(
        """select score, score_detail, first_signal_at, scored_at is not null
           from public.sites where label like 'NTT%'"""
    ).fetchone()
    # Two monitor wells submitted on August 21, 2026, 91 days before. One type, counted once.
    assert float(score) == pytest.approx(15 * 0.9 * 0.5 ** (91 / 365), abs=0.01)
    assert detail["signals_total"] == 2 and detail["signals_counted"] == 1
    assert detail["contributions"][0]["signal_type"] == "well_report"
    assert detail["bonus"] == {"points": 0.0, "types": []}
    assert detail["placeholder"] is True
    assert first == dt.datetime(2026, 8, 21, tzinfo=dt.UTC) and scored


def test_a_site_sits_at_the_middle_of_its_signals_coordinates(radar):
    radar.run()
    lon, lat = radar.conn.execute(
        """select extensions.st_x(geom), extensions.st_y(geom) from public.sites
           where label like 'NTT%'"""
    ).fetchone()
    assert lon == pytest.approx((-97.56904 + -97.563472) / 2, abs=1e-6)
    assert lat == pytest.approx((30.40553 + 30.40529) / 2, abs=1e-6)


def test_each_signal_says_why_it_is_on_its_site(radar):
    radar.run()
    links = radar.conn.execute(
        """select extracted->>'site_link' from public.signals sg
           join public.sites s on s.id = sg.site_id where s.label like 'NTT%'
           order by sg.event_date, sg.id"""
    ).fetchall()
    assert links == [("the first signal of this site",), ("the same company",)]


def test_a_second_type_within_a_year_earns_the_bonus_and_the_site_enters_the_queue(radar):
    radar.run()
    radar.add_signal("NTT%", "transmission_filing", days_ago=30)
    summary = radar.run()

    assert summary.detail["sites"]["signals_attached"] == 1
    assert summary.detail["sites"]["sites_new"] == 0
    assert summary.detail["sites"]["moved_to_review"] == 1
    _, _, _, status, score, n = next(s for s in radar.sites() if s[1].startswith("NTT"))
    expected = 15 * 0.9 * 0.5 ** (91 / 365) + 30 * 0.9 * 0.5 ** (30 / 365) + 20
    assert float(score) == pytest.approx(expected, abs=0.01) and score >= THRESHOLD
    assert (status, n) == ("in_review", 3)
    detail = radar.conn.execute(
        "select score_detail from public.sites where label like 'NTT%'"
    ).fetchone()[0]
    assert detail["bonus"] == {"points": 20.0, "types": ["transmission_filing", "well_report"]}


def test_scores_decay_and_a_site_is_never_taken_out_of_the_queue(radar):
    radar.run()
    radar.add_signal("NTT%", "transmission_filing", days_ago=30)
    radar.run()
    later = radar.run(as_of=AS_OF + dt.timedelta(days=3 * 365))
    assert later.documents == 0
    _, _, _, status, score, _ = next(s for s in radar.sites() if s[1].startswith("NTT"))
    assert score < THRESHOLD  # the points faded. The bonus alone is below the threshold.
    assert status == "in_review"
    assert later.detail["sites"]["moved_to_review"] == 0


def test_a_second_run_changes_nothing(radar):
    radar.run()
    before = radar.sites()
    again = radar.run()
    assert radar.sites() == before
    assert again.detail["sites"]["sites_new"] == 0
    assert again.detail["sites"]["signals_attached"] == 0


def test_a_rejected_site_keeps_its_signals_and_stays_rejected(radar):
    radar.run()
    site_id = radar.site("NTT%")
    radar.conn.execute("update public.sites set status = 'rejected' where id = %s", [site_id])
    radar.add_signal("NTT%", "transmission_filing", days_ago=5)
    summary = radar.run()
    _, _, _, status, score, n = next(s for s in radar.sites() if s[1].startswith("NTT"))
    assert (status, n) == ("rejected", 3)
    assert score >= THRESHOLD  # still scored, so an administrator can see what arrived
    assert summary.detail["sites"]["moved_to_review"] == 0


def test_the_same_company_far_away_in_the_county_starts_another_site(radar):
    radar.run()
    # About 40 km east of the first site, inside the same county for the test's purposes.
    radar.add_signal("NTT%", "transmission_filing", point=(-97.15, 30.40))
    summary = radar.run()
    assert summary.detail["sites"]["sites_new"] == 1
    labels = [s[1] for s in radar.sites()]
    assert labels.count("NTT Global Data Centers AUI, LLC, Travis County") == 2


def test_a_signal_that_fits_two_sites_joins_the_older_one_and_is_flagged(radar):
    radar.run()
    first = radar.site("NTT%")
    # Another company starts a site 2 km east. Then the first company files right next to it.
    radar.add_signal("NTT%", "air_permit", other_company="Invented Neighbor LLC",
                     point=(-97.5455, 30.4054))  # fmt: skip
    radar.run()
    second = radar.site("Invented Neighbor%")
    joiner = radar.add_signal("NTT%", "transmission_filing", point=(-97.5460, 30.4054))
    summary = radar.run()
    assert summary.detail["sites"]["possible_same_site"] == [
        {"signal_id": joiner, "sites": [first, second]}
    ]
    assert radar.conn.execute(
        "select site_id from public.signals where id = %s", [joiner]
    ).fetchone() == (first,)


def test_a_reviewer_reads_sites_scores_and_breakdowns(radar):
    radar.run()
    reviewer = make_reviewer(radar.conn)
    with as_user(radar.conn, reviewer):
        rows = radar.conn.execute(
            "select label, score > 0, score_detail ? 'contributions' from public.sites"
            " where label like 'NTT%'"
        ).fetchall()
    assert rows == [("NTT Global Data Centers AUI, LLC, Travis County", True, True)]


def test_sites_can_be_scored_without_reading_documents(radar):
    radar.run()
    with as_service(radar.conn):
        summary = update_sites(radar.conn, as_of=AS_OF + dt.timedelta(days=365))
    assert summary["sites_scored"] == 2 and summary["sites_new"] == 0
    score = radar.conn.execute("select score from public.sites where label like 'NTT%'").fetchone()[
        0
    ]
    assert float(score) == pytest.approx(15 * 0.9 * 0.5 ** ((91 + 365) / 365), abs=0.01)


def test_the_run_log_carries_the_site_summary(radar):
    radar.run(runner="test")
    detail = radar.conn.execute(
        "select detail from public.processing_runs order by id desc limit 1"
    ).fetchone()[0]
    assert detail["sites"]["sites_new"] == 2 and detail["sites"]["unplaced"] == 6
