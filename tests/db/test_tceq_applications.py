"""Air permit signals get their county from the application file each row links.

The web here is a stand-in. No test fetches a real file.
"""

from __future__ import annotations

import datetime as dt

import httpx
import pytest

from collectors.base import Fetcher
from pipeline import process, tceq_applications
from pipeline.config import load_sources
from pipeline.geocode import ArchivedLookup

from ..helpers import CONTACT, FakeClock, Site, make_pdf
from ..test_tceq_applications import FORM, LETTER
from .conftest import as_service, as_user, make_reviewer
from .test_process import Stored

pytestmark = pytest.mark.db

SOURCE = load_sources().by_id(tceq_applications.SOURCE_ID)
AS_OF = dt.date(2026, 11, 20)
ARMSTRONG = LETTER.replace("Midlothian, Ellis", "Claude, Armstrong")


class Radar(Stored):
    def rows(self) -> dict[str, tuple]:
        """Each air permit signal by permit number: its id, application file and county."""
        found = self.conn.execute(
            """select extracted->'row'->>'permit_number', id,
                      extracted->'row'->>'application_url', county_fips, site_id
               from public.signals where signal_type = 'air_permit'"""
        ).fetchall()
        return {r[0]: r[1:] for r in found}

    def run(self, web: Site | None = None, **kwargs) -> process.ProcessSummary:
        with as_service(self.conn):
            if web is None:
                return process.run(self.conn, self.store, as_of=AS_OF, **kwargs)
            clock = FakeClock()
            with Fetcher(
                SOURCE, contact=CONTACT, transport=web.transport, clock=clock, sleep=clock.sleep
            ) as fetcher:
                lookup = ArchivedLookup(SOURCE, fetcher, self.store, self.sink)
                return process.run(
                    self.conn,
                    self.store,
                    as_of=AS_OF,
                    enrich=lambda: tceq_applications.enrich_air_permits(
                        self.conn, source=SOURCE, lookup=lookup, sink=self.sink
                    ),
                    **kwargs,
                )

    def application(self, permit: str) -> dict:
        return self.conn.execute(
            """select extracted->'application' from public.signals
               where extracted->'row'->>'permit_number' = %s""",
            [permit],
        ).fetchone()[0]


@pytest.fixture
def radar(db, tmp_path) -> Radar:
    made = Radar(db, tmp_path)
    made.add_everything()
    made.run()  # six air permit signals, none with a county
    return made


def pdf(text: str) -> httpx.Response:
    return httpx.Response(
        200, content=make_pdf([text]), headers={"content-type": "application/pdf"}
    )


def web_for(radar: Radar, answers: dict[str, httpx.Response]) -> Site:
    rows = radar.rows()
    return Site({rows[permit][1]: answer for permit, answer in answers.items()})


ALIGNED, TESLA = "131651", "162531, GHGPSDTX274, PSDTX1708"


def test_without_the_step_no_file_is_fetched_and_no_signal_has_a_county(radar):
    assert len(radar.rows()) == 6
    assert all(county is None for _, _, county, _ in radar.rows().values())


def test_a_signal_gets_the_county_its_application_states(radar):
    web = web_for(radar, {ALIGNED: pdf(FORM), TESLA: pdf(ARMSTRONG)})
    summary = radar.run(web)

    done = summary.detail["tceq_applications"]
    assert (done["asked"], done["read"], done["in_scope"], done["out_of_scope"]) == (6, 2, 1, 1)
    assert done["fetch_failed"] == 4  # the stand-in web has no file for the other four

    rows = radar.rows()
    assert rows[ALIGNED][2] == "48139"
    record = radar.application(ALIGNED)
    assert record["status"] == "read" and record["county"] == "Ellis"
    assert record["evidence"] == ["County ELLIS"]
    assert record["url"] == rows[ALIGNED][1]
    assert (record["street"], record["primary_business"]) == ("100 EXAMPLE PKWY", "DATA CENTER")
    point = radar.conn.execute(
        "select extracted->'point' from public.signals where id = %s", [rows[ALIGNED][0]]
    ).fetchone()[0]
    assert (point["lon"], point["lat"]) == (-97.059166, 32.443055)


def test_a_county_outside_the_test_set_is_recorded_and_the_signal_stays_unplaced(radar):
    radar.run(web_for(radar, {TESLA: pdf(ARMSTRONG)}))
    assert radar.rows()[TESLA][2] is None
    record = radar.application(TESLA)
    assert (record["county"], record["in_scope"]) == ("Armstrong", False)


def test_the_signal_then_joins_a_site_and_the_site_gets_its_place(radar):
    summary = radar.run(web_for(radar, {ALIGNED: pdf(FORM)}))
    assert summary.detail["sites"]["sites_new"] == 1
    label, county, lon = radar.conn.execute(
        """select s.label, s.county_fips, extensions.st_x(s.geom)
           from public.sites s join public.signals sg on sg.site_id = s.id
           where sg.id = %s""",
        [radar.rows()[ALIGNED][0]],
    ).fetchone()
    assert (label, county) == ("ALIGNED DATA CENTERS REIT LLC, Ellis County", "48139")
    assert lon == pytest.approx(-97.059166)


def test_each_file_is_fetched_once_and_stored_restricted(radar):
    web = web_for(radar, {ALIGNED: pdf(FORM)})
    radar.run(web)
    url = radar.rows()[ALIGNED][1]
    asked = [u for u in web.page_urls() if u == url]
    assert len(asked) == 1

    again = radar.run(web)
    assert [u for u in web.page_urls() if u == url] == asked  # no second request
    assert again.detail["tceq_applications"]["read"] == 0

    doc_id, restricted, sha = radar.conn.execute(
        "select id, restricted, sha256 from public.documents where url = %s", [url]
    ).fetchone()
    assert restricted is True
    assert radar.application(ALIGNED)["document_sha256"] == sha
    reviewer = make_reviewer(radar.conn)
    with as_user(radar.conn, reviewer):
        assert radar.conn.execute(
            "select count(*) from public.documents where id = %s", [doc_id]
        ).fetchone() == (0,)
        # The reviewer still reads the county and address lines on the signal.
        assert radar.conn.execute(
            "select extracted->'application'->>'county' from public.signals where id = %s",
            [radar.rows()[ALIGNED][0]],
        ).fetchone() == ("Ellis",)


def test_the_application_file_itself_makes_no_signal_and_no_error(radar):
    before = radar.conn.execute("select count(*) from public.signals").fetchone()[0]
    summary = radar.run(web_for(radar, {ALIGNED: pdf(FORM)}))
    later = radar.run()  # the stored file is now one of the documents waiting to be read
    assert (summary.errors, later.errors) == (0, 0)
    assert radar.conn.execute("select count(*) from public.signals").fetchone()[0] == before


def test_a_file_that_could_not_be_fetched_is_tried_again_next_run(radar):
    first = radar.run(Site({}))  # nothing answers
    assert first.detail["tceq_applications"]["fetch_failed"] == 6
    assert radar.application(ALIGNED)["status"] == "fetch_failed"
    second = radar.run(web_for(radar, {ALIGNED: pdf(FORM)}))
    assert second.detail["tceq_applications"]["in_scope"] == 1
    assert radar.rows()[ALIGNED][2] == "48139"


def test_a_file_with_two_counties_or_none_leaves_the_signal_without_one(radar):
    both = FORM + "\n" + LETTER.replace("Ellis", "Dallas")
    radar.run(web_for(radar, {ALIGNED: pdf(both), TESLA: pdf("Nothing about a place.")}))
    assert radar.rows()[ALIGNED][2] is None and radar.rows()[TESLA][2] is None
    assert radar.application(ALIGNED)["status"] == "ambiguous"
    assert radar.application(ALIGNED)["counties_read"] == ["Dallas", "Ellis"]
    assert radar.application(TESLA)["status"] == "no_county"
    # Both were read, so neither is fetched or read again.
    again = radar.run(Site({}))
    assert again.detail["tceq_applications"]["asked"] == 4


def test_a_refusal_stops_the_step_and_is_reported(radar):
    web = web_for(radar, {ALIGNED: httpx.Response(403)})
    summary = radar.run(web)
    done = summary.detail["tceq_applications"]
    assert "403" in done["stopped"]
    assert done["asked"] == 0
    assert summary.status == "ok"  # the documents were still read and the sites still scored
    assert "sites" in summary.detail


def test_a_file_over_the_size_limit_is_recorded_and_not_asked_for_again(radar, monkeypatch):
    from collectors import base

    monkeypatch.setattr(base, "MAX_BODY_BYTES", 500)
    web = web_for(radar, {ALIGNED: pdf(FORM + "\n" + "x" * 2000)})
    radar.run(web)
    assert radar.application(ALIGNED)["status"] == "too_large"
    assert radar.application(ALIGNED)["limit_mb"] == 50
    again = radar.run(web)
    assert again.detail["tceq_applications"]["too_large"] == 0
    assert again.detail["tceq_applications"]["asked"] == 5


def test_a_file_that_was_too_large_is_asked_for_again_once_the_limit_is_raised(radar, monkeypatch):
    from collectors import base

    monkeypatch.setattr(base, "MAX_BODY_BYTES", 500)
    web = web_for(radar, {ALIGNED: pdf(FORM + "\n" + "x" * 2000)})
    radar.run(web)
    assert radar.application(ALIGNED)["status"] == "too_large"

    raised = SOURCE.model_copy(update={"max_body_mb": 60})
    with as_service(radar.conn):
        clock = FakeClock()
        with Fetcher(
            raised, contact=CONTACT, transport=web.transport, clock=clock, sleep=clock.sleep
        ) as fetcher:
            lookup = ArchivedLookup(raised, fetcher, radar.store, radar.sink)
            done = tceq_applications.enrich_air_permits(
                radar.conn, source=raised, lookup=lookup, sink=radar.sink
            )
    assert done["in_scope"] == 1 and radar.rows()[ALIGNED][2] == "48139"


def test_a_limit_bounds_how_many_files_one_run_fetches(radar):
    web = web_for(radar, {ALIGNED: pdf(FORM)})
    with as_service(radar.conn):
        clock = FakeClock()
        with Fetcher(
            SOURCE, contact=CONTACT, transport=web.transport, clock=clock, sleep=clock.sleep
        ) as fetcher:
            lookup = ArchivedLookup(SOURCE, fetcher, radar.store, radar.sink)
            done = tceq_applications.enrich_air_permits(
                radar.conn, source=SOURCE, lookup=lookup, sink=radar.sink, limit=2
            )
    assert done["asked"] == 2
