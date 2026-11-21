"""The Legistar agenda collector, run against saved answers from the Legistar Web API.

The list of Round Rock's meetings and one Round Rock meeting were saved with collectors.capture.
The Harris County meeting is a trimmed copy: the real answer holds 1,740 items and names many
people, so the fixture keeps seven items that name none. Its .meta.json says so. No test here
touches the network.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import httpx
import pytest

from collectors.base import Fetcher, LayoutChanged, LocalArchive
from collectors.tx.legistar import (
    Client,
    LegistarAgendas,
    cleared_clients,
    client_name,
    event_url,
    events_url,
    reduce_event,
)
from pipeline.config import load_sources
from pipeline.store import MemorySink

from .helpers import CONTACT, FakeClock, Site

FIXTURES = Path(__file__).parent / "fixtures" / "tx_agendas_legistar"


def fixture(name: str) -> tuple[bytes, dict]:
    body = (FIXTURES / f"{name}.txt").read_bytes()
    return body, json.loads((FIXTURES / f"{name}.meta.json").read_text())


LIST_BODY, LIST_META = fixture("roundrock-events")
EVENT_BODY, EVENT_META = fixture("roundrock-event-3430")
HARRIS_BODY, HARRIS_META = fixture("harris-event-1244-trimmed")

ROUND_ROCK = Client("roundrock", "Round Rock city", ("Travis",))
HARRIS = Client("harriscountytx", "Harris County", ("Harris",))
# The day the list was saved for: it asks for meetings from November 7 on.
TODAY = dt.date(2026, 11, 21)
LIST_URL = events_url("roundrock", dt.date(2026, 11, 7))
MEETINGS = json.loads(LIST_BODY)


def source():
    return load_sources().by_id("tx_agendas_legistar")


def stand_in(event: dict) -> httpx.Response:
    """A meeting with no agenda items, in the API's shape, for meetings with no saved answer."""
    return httpx.Response(200, json={**event, "EventItems": []})


def web(meetings: list[dict] | None = None, **more) -> Site:
    meetings = MEETINGS if meetings is None else meetings
    routes: dict[str, object] = {LIST_URL: httpx.Response(200, json=meetings)}
    for event in meetings:
        url = event_url("roundrock", event["EventId"])
        routes[url] = (
            httpx.Response(200, content=EVENT_BODY) if event["EventId"] == 3430 else stand_in(event)
        )
    routes.update(more)
    # No Legistar host has a robots file. The fetcher reads a 404 as no rules.
    return Site(routes, robots=404)


def run(site: Site, sink: MemorySink, tmp_path, clients=(ROUND_ROCK,), **kwargs):
    clock = FakeClock()
    collector = LegistarAgendas(clients=clients, today=TODAY, **kwargs)
    with Fetcher(
        source(), contact=CONTACT, transport=site.transport, clock=clock, sleep=clock.sleep
    ) as fetcher:
        return collector.run(
            source=source(), fetcher=fetcher, store=LocalArchive(tmp_path), sink=sink
        )


def stored(sink: MemorySink, tmp_path, url: str) -> dict:
    doc = next(d for d in sink.documents.values() if d.url == url)
    return json.loads(LocalArchive(tmp_path).get(doc.storage_path))


# --- addresses ----------------------------------------------------------------------------------


def test_the_saved_answers_are_the_ones_the_collector_asks_for():
    assert LIST_META["url"] == LIST_URL
    assert EVENT_META["url"] == event_url("roundrock", 3430)
    assert HARRIS_META["url"] == event_url("harriscountytx", 1244)
    assert HARRIS_META["trimmed"] is True and HARRIS_META["original_items"] == 1740


def test_a_client_name_is_read_from_a_governments_legistar_address():
    assert client_name("https://roundrock.legistar.com/Calendar.aspx") == "roundrock"
    assert client_name(
        "https://agenda.harriscountytx.gov/", "https://harriscountytx.legistar.com/"
    ) == ("harriscountytx")
    assert client_name("https://webapi.legistar.com/v1/roundrock/events") is None
    assert client_name("https://www.roundrocktexas.gov/", "") is None
    with pytest.raises(ValueError, match="not a Legistar client name"):
        Client("round rock/../x", "Round Rock city", ("Travis",))


# --- what is kept of a meeting ------------------------------------------------------------------


def test_a_meeting_is_cut_down_to_what_the_radar_reads():
    agenda = reduce_event(json.loads(EVENT_BODY), ROUND_ROCK)
    assert {k: agenda[k] for k in ("client", "government", "counties", "event_id", "body")} == {
        "client": "roundrock",
        "government": "Round Rock city",
        "counties": ["Travis"],
        "event_id": 3430,
        "body": "City Council",
    }
    assert (agenda["date"], agenda["agenda_status"]) == ("2026-11-19", "Final")
    assert agenda["page"].startswith("https://roundrock.legistar.com/MeetingDetail.aspx")
    assert len(agenda["items"]) == 29
    assert [i["sequence"] for i in agenda["items"]] == sorted(
        i["sequence"] for i in agenda["items"]
    )
    first = agenda["items"][0]
    assert (first["number"], first["title"]) == ("A.", "CALL MEETING TO ORDER")
    eminent = next(i for i in agenda["items"] if i["file"] == "2026-280")
    assert eminent["type"] == "Resolution" and "eminent domain" in eminent["title"]
    assert "\n" not in eminent["title"] and "  " not in eminent["title"]


def test_who_moved_and_voted_is_left_behind():
    data = json.loads(EVENT_BODY)
    data["EventItems"][0]["EventItemMover"] = "A Council Member"
    data["EventItems"][0]["EventItemSeconder"] = "Another Council Member"
    agenda = reduce_event(data, ROUND_ROCK)
    assert set(agenda["items"][0]) == {
        "id", "sequence", "number", "file", "type", "name", "title", "note"
    }  # fmt: skip
    assert "Council Member" not in json.dumps(agenda)
    # The agenda file sits on a host that bars robots. Its address is not kept either.
    assert "EventAgendaFile" in data and "legistar1.com" not in json.dumps(agenda)


def test_a_real_item_about_data_centers_comes_through_whole():
    agenda = reduce_event(json.loads(HARRIS_BODY), HARRIS)
    item = next(i for i in agenda["items"] if i["file"] == "26-6897")
    assert item["number"] == "343."
    assert item["title"].startswith(
        "Request for discussion and possible action regarding data center"
    )
    assert (agenda["body"], agenda["date"], agenda["agenda_status"]) == (
        "Commissioners Court", "2026-10-15", "Closed"
    )  # fmt: skip


@pytest.mark.parametrize(
    "data",
    [[], {"EventId": 1}, {"EventId": 1, "EventItems": "none"}, {"EventId": 1, "EventItems": [1]}],
)
def test_an_answer_that_is_not_a_meeting_stops_the_reader(data):
    with pytest.raises(LayoutChanged):
        reduce_event(data, ROUND_ROCK)


def test_a_meeting_with_no_readable_date_stops_the_reader():
    data = {**json.loads(EVENT_BODY), "EventDate": "next Thursday"}
    with pytest.raises(LayoutChanged, match="not a date"):
        reduce_event(data, ROUND_ROCK)


# --- a run --------------------------------------------------------------------------------------


def test_a_run_reads_the_list_and_then_each_published_agenda(tmp_path):
    site, sink = web(), MemorySink()
    summary = run(site, sink, tmp_path)
    assert summary.status == "ok", summary.error
    assert site.page_urls() == [LIST_URL] + [event_url("roundrock", e["EventId"]) for e in MEETINGS]
    assert (summary.documents_seen, summary.documents_new) == (5, 5)
    agenda = stored(sink, tmp_path, event_url("roundrock", 3430))
    assert agenda["body"] == "City Council" and len(agenda["items"]) == 29
    doc = next(d for d in sink.documents.values() if d.url == event_url("roundrock", 3430))
    assert doc.raw_meta["record"] == "legistar_agenda"
    assert (doc.raw_meta["government"], doc.raw_meta["counties"]) == ("Round Rock city", ["Travis"])
    assert doc.raw_meta["original_kept"] is False and doc.raw_meta["original_bytes"] == len(
        EVENT_BODY
    )
    assert sink.runs[1]["detail"]["governments"] == ["roundrock"]


def test_only_the_published_api_is_asked_and_never_the_agenda_file(tmp_path):
    site = web()
    run(site, MemorySink(), tmp_path)
    assert {httpx.URL(u).host for u in site.urls()} == {"webapi.legistar.com"}
    assert not [u for u in site.urls() if u.endswith(".pdf")]
    assert all(r.headers["user-agent"].startswith("DataCenterRadar/") for r in site.requests)


def test_a_second_run_asks_only_for_the_list_when_nothing_changed(tmp_path):
    site, sink = web(), MemorySink()
    run(site, sink, tmp_path)
    again = web()
    summary = run(again, sink, tmp_path)
    assert again.page_urls() == [LIST_URL]
    assert (summary.status, summary.documents_new) == ("ok", 0)


def test_a_meeting_that_changed_is_read_again(tmp_path):
    sink = MemorySink()
    run(web(), sink, tmp_path)
    changed = [dict(e) for e in MEETINGS]
    target = next(e for e in changed if e["EventId"] == 3430)
    target["EventLastModifiedUtc"] = "2026-11-18T09:00:00.000"
    revised = json.loads(EVENT_BODY)
    revised["EventLastModifiedUtc"] = target["EventLastModifiedUtc"]
    revised["EventItems"][13]["EventItemTitle"] = "Consider a resolution on a matter added late."
    url = event_url("roundrock", 3430)
    site = web(changed, **{url: httpx.Response(200, json=revised)})
    summary = run(site, sink, tmp_path)
    assert site.page_urls() == [LIST_URL, url]
    assert summary.documents_new == 2  # the list, which changed too, and the agenda
    newest = max((d for d in sink.documents.values() if d.url == url), key=lambda d: d.retrieved_at)
    assert newest.raw_meta["event_modified"] == "2026-11-18T09:00:00.000"


def test_a_meeting_with_no_published_agenda_is_not_asked_for(tmp_path):
    meetings = [dict(e) for e in MEETINGS]
    meetings[0]["EventAgendaLastPublishedUTC"] = None
    site = web(meetings)
    run(site, MemorySink(), tmp_path)
    assert event_url("roundrock", meetings[0]["EventId"]) not in site.page_urls()
    assert len(site.page_urls()) == 4


def test_a_first_run_on_a_busy_government_leaves_the_rest_for_next_time(tmp_path):
    site, sink = web(), MemorySink()
    collector = LegistarAgendas(clients=(ROUND_ROCK,), today=TODAY)
    collector.max_events_per_client = 2
    clock = FakeClock()
    with Fetcher(
        source(), contact=CONTACT, transport=site.transport, clock=clock, sleep=clock.sleep
    ) as fetcher:
        summary = collector.run(
            source=source(), fetcher=fetcher, store=LocalArchive(tmp_path), sink=sink
        )
    assert len(site.page_urls()) == 3
    assert summary.detail["held_over"] == {"roundrock": 2}
    # The next run picks up the two that waited.
    later = web()
    run(later, sink, tmp_path)
    assert len(later.page_urls()) == 3


def test_requests_to_one_host_are_spaced_out(tmp_path):
    clock = FakeClock()
    site = web()
    collector = LegistarAgendas(clients=(ROUND_ROCK,), today=TODAY)
    with Fetcher(
        source(), contact=CONTACT, transport=site.transport, clock=clock, sleep=clock.sleep
    ) as fetcher:
        collector.run(
            source=source(), fetcher=fetcher, store=LocalArchive(tmp_path), sink=MemorySink()
        )
    # Six requests to the one host, robots file included: five waits of five seconds.
    assert clock() >= 25


def test_a_robots_file_that_bars_the_api_ends_the_run(tmp_path):
    site = Site(
        {LIST_URL: httpx.Response(200, json=MEETINGS)}, robots="User-agent: *\nDisallow: /\n"
    )
    summary = run(site, MemorySink(), tmp_path)
    assert summary.status == "blocked"
    assert site.page_urls() == []


def test_a_refusal_from_the_api_ends_the_run(tmp_path):
    site = Site({LIST_URL: httpx.Response(403)}, robots=404)
    summary = run(site, MemorySink(), tmp_path)
    assert summary.status == "blocked"
    assert site.page_urls() == [LIST_URL]


def test_an_answer_in_another_shape_stops_the_run_and_stores_nothing_of_it(tmp_path):
    site, sink = (
        Site({LIST_URL: httpx.Response(200, json={"Message": "moved"})}, robots=404),
        MemorySink(),
    )
    summary = run(site, sink, tmp_path)
    assert summary.status == "failed" and "not a list" in summary.error
    assert not sink.documents


def test_two_governments_are_read_in_one_run(tmp_path):
    harris_list = events_url("harriscountytx", dt.date(2026, 11, 7))
    harris_meeting = json.loads(HARRIS_BODY)
    listed = {k: v for k, v in harris_meeting.items() if k != "EventItems"}
    site = web(
        **{
            harris_list: httpx.Response(200, json=[listed]),
            event_url("harriscountytx", 1244): httpx.Response(200, content=HARRIS_BODY),
        }
    )
    sink = MemorySink()
    summary = run(site, sink, tmp_path, clients=(ROUND_ROCK, HARRIS))
    assert summary.status == "ok", summary.error
    agenda = stored(sink, tmp_path, event_url("harriscountytx", 1244))
    assert agenda["government"] == "Harris County" and len(agenda["items"]) == 7
    assert sink.runs[1]["detail"]["governments"] == ["harriscountytx", "roundrock"]


# --- which governments --------------------------------------------------------------------------


def test_the_governments_read_are_the_ones_the_inventory_clears():
    """Nine of the 14 on Legistar. The others are held out, each for a stated reason."""
    names = [c.name for c in cleared_clients(dt.date(2026, 11, 21))]
    assert names == [
        "carrolltontx", "cityofdallas", "cityofdeerpark", "cityoflewisville", "coppell",
        "farmersbranch", "harriscountytx", "pflugerville", "roundrock",
    ]  # fmt: skip
    # Their own terms ask for written consent to reuse, their site was not read, or they left.
    for held in ("leaguecity", "lubbockcounty", "fortworthgov", "uptexas", "sanantonio"):
        assert held not in names


def test_a_check_that_has_gone_stale_clears_no_one():
    assert cleared_clients(dt.date(2027, 11, 21)) == []
