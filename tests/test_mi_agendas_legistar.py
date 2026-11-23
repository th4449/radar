"""The Legistar agenda collector for Michigan, run against saved answers from the Legistar Web API.

The list of Ann Arbor's meetings and one council meeting were saved with collectors.capture on
November 23, 2026. The council meeting is a trimmed copy: two of its 49 items name people who
signed up to speak, and the fixture leaves those two out. The list has each meeting's comment
emptied: the comments gave call-in passcodes. Each .meta.json says so. No test here touches the
network.

The source is marked manual: no job reads it until the owner says so. The run tests use a copy
of the source marked http, as it will be then.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import httpx
import pytest

from collectors import run as runner
from collectors.base import Fetcher, LocalArchive, NotPermitted
from collectors.mi.legistar import MichiganLegistarAgendas
from collectors.tx.legistar import (
    Client,
    LegistarAgendas,
    cleared_clients,
    event_url,
    events_url,
    reduce_event,
)
from pipeline.config import load_sources
from pipeline.store import MemorySink

from .helpers import CONTACT, FakeClock, Site

FIXTURES = Path(__file__).parent / "fixtures" / "mi_agendas_legistar"


def fixture(name: str) -> tuple[bytes, dict]:
    body = (FIXTURES / f"{name}.txt").read_bytes()
    return body, json.loads((FIXTURES / f"{name}.meta.json").read_text())


LIST_BODY, LIST_META = fixture("a2gov-events")
EVENT_BODY, EVENT_META = fixture("a2gov-event-14163-trimmed")

ANN_ARBOR = Client("a2gov", "Ann Arbor city", ("Washtenaw",))
# The day the list was saved: it asks for meetings from November 9 on.
TODAY = dt.date(2026, 11, 23)
LIST_URL = events_url("a2gov", dt.date(2026, 11, 9))
MEETINGS = json.loads(LIST_BODY)
PUBLISHED = [e for e in MEETINGS if e["EventAgendaLastPublishedUTC"]]


def source():
    return load_sources().by_id("mi_agendas_legistar")


def cleared_to_run():
    """The source as it will be once the owner says to run it."""
    return source().model_copy(update={"method": "http"})


def web() -> Site:
    routes: dict[str, object] = {LIST_URL: httpx.Response(200, content=LIST_BODY)}
    for event in MEETINGS:
        url = event_url("a2gov", event["EventId"])
        routes[url] = (
            httpx.Response(200, content=EVENT_BODY)
            if event["EventId"] == 14163
            else httpx.Response(200, json={**event, "EventItems": []})
        )
    # No Legistar host has a robots file. The fetcher reads a 404 as no rules.
    return Site(routes, robots=404)


def run(site: Site, sink: MemorySink, tmp_path, **kwargs):
    clock = FakeClock()
    collector = MichiganLegistarAgendas(clients=(ANN_ARBOR,), today=TODAY, **kwargs)
    with Fetcher(
        cleared_to_run(), contact=CONTACT, transport=site.transport, clock=clock, sleep=clock.sleep
    ) as fetcher:
        return collector.run(
            source=cleared_to_run(), fetcher=fetcher, store=LocalArchive(tmp_path), sink=sink
        )


# --- the saved answers --------------------------------------------------------------------------


def test_the_saved_answers_are_the_ones_the_collector_asks_for():
    assert LIST_META["url"] == LIST_URL
    assert EVENT_META["url"] == event_url("a2gov", 14163)
    assert LIST_META["source_id"] == EVENT_META["source_id"] == "mi_agendas_legistar"
    assert EVENT_META["trimmed"] is True
    assert (EVENT_META["original_items"], EVENT_META["items_kept"]) == (49, 47)


def test_the_api_answered_for_ann_arbor_without_a_token():
    # Some governments ask for one. Ann Arbor's answer was the list itself: eight meetings in
    # two weeks, six with a published agenda.
    assert isinstance(MEETINGS, list) and len(MEETINGS) == 8
    assert len(PUBLISHED) == 6
    assert {e["EventBodyName"] for e in MEETINGS} >= {"City Council", "Housing Commission"}


def test_the_saved_meeting_names_no_one_who_spoke_and_no_one_who_moved():
    items = json.loads(EVENT_BODY)["EventItems"]
    assert len(items) == 47
    assert not [i for i in items if "(In Person)" in (i["EventItemTitle"] or "")]
    assert not [i for i in items if i["EventItemMover"] or i["EventItemSeconder"]]
    assert not [i for i in items if i["EventItemMatterAttachments"] or i["EventItemActionText"]]


# --- which governments --------------------------------------------------------------------------


def test_one_michigan_government_is_read_and_it_is_ann_arbor():
    assert cleared_clients(TODAY, state="MI") == [ANN_ARBOR]


def test_the_michigan_collector_reads_michigans_inventory_and_the_texas_one_reads_texas():
    michigan = MichiganLegistarAgendas(today=TODAY)
    assert list(michigan.clients) == ["a2gov"]
    assert michigan.urls() == [LIST_URL]
    texas = LegistarAgendas(today=TODAY)
    assert "a2gov" not in texas.clients and "roundrock" in texas.clients
    assert (michigan.source_id, texas.source_id) == ("mi_agendas_legistar", "tx_agendas_legistar")


# --- what is kept of a meeting ------------------------------------------------------------------


def test_an_ann_arbor_meeting_is_cut_down_to_what_the_radar_reads():
    agenda = reduce_event(json.loads(EVENT_BODY), ANN_ARBOR)
    assert {k: agenda[k] for k in ("client", "government", "counties", "event_id", "body")} == {
        "client": "a2gov",
        "government": "Ann Arbor city",
        "counties": ["Washtenaw"],
        "event_id": 14163,
        "body": "City Council",
    }
    assert (agenda["date"], agenda["agenda_status"]) == ("2026-11-16", "Final-revised")
    assert agenda["page"].startswith("https://a2gov.legistar.com/MeetingDetail.aspx")
    assert len(agenda["items"]) == 47
    assert [i["sequence"] for i in agenda["items"]] == sorted(
        i["sequence"] for i in agenda["items"]
    )
    minutes = next(i for i in agenda["items"] if i["file"] == "26-1482")
    assert (minutes["number"], minutes["type"]) == ("F-2", "Minutes")
    assert minutes["title"] == "City Planning Commission Meeting Minutes of September 1, 2026"
    assert set(agenda["items"][0]) == {
        "id", "sequence", "number", "file", "type", "name", "title", "note"
    }  # fmt: skip
    # The agenda file sits on a host that was not read. Its address is not kept.
    assert "legistar1.com" not in json.dumps(agenda)


# --- a run --------------------------------------------------------------------------------------


def test_a_run_reads_the_list_and_then_each_published_agenda(tmp_path):
    site, sink = web(), MemorySink()
    summary = run(site, sink, tmp_path)
    assert summary.status == "ok", summary.error
    assert site.page_urls() == [LIST_URL] + [event_url("a2gov", e["EventId"]) for e in PUBLISHED]
    assert (summary.documents_seen, summary.documents_new) == (7, 7)
    doc = next(d for d in sink.documents.values() if d.url == event_url("a2gov", 14163))
    assert doc.source_id == "mi_agendas_legistar"
    assert doc.raw_meta["record"] == "legistar_agenda"
    assert (doc.raw_meta["government"], doc.raw_meta["counties"]) == (
        "Ann Arbor city",
        ["Washtenaw"],
    )
    assert (doc.raw_meta["event_date"], doc.raw_meta["items"]) == ("2026-11-16", 47)
    assert sink.runs[1]["detail"]["governments"] == ["a2gov"]


def test_only_the_published_api_is_asked_and_never_the_agenda_file(tmp_path):
    site = web()
    run(site, MemorySink(), tmp_path)
    assert {httpx.URL(u).host for u in site.urls()} == {"webapi.legistar.com"}
    assert not [u for u in site.urls() if u.endswith(".pdf")]
    assert all(r.headers["user-agent"].startswith("DataCenterRadar/") for r in site.requests)


def test_a_second_run_asks_only_for_the_list_when_nothing_changed(tmp_path):
    sink = MemorySink()
    run(web(), sink, tmp_path)
    again = web()
    summary = run(again, sink, tmp_path)
    assert again.page_urls() == [LIST_URL]
    assert (summary.status, summary.documents_new) == ("ok", 0)


# --- not yet ------------------------------------------------------------------------------------


def test_no_job_can_start_the_source_while_it_is_marked_manual():
    # The collector is written and is not on the list of collectors a job can run. It goes on
    # that list, with a workflow file, when the owner says to run it.
    assert source().method == "manual" and "mi_agendas_legistar" not in runner.REGISTRY
    with pytest.raises(runner.CannotStart):
        runner.run_source(source(), dry_run=True, contact=CONTACT)
    with pytest.raises(NotPermitted, match="collected by a person"):
        Fetcher(source(), contact=CONTACT)
