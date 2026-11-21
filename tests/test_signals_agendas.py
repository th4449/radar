"""Agenda items become signals. Read from saved answers of the Legistar Web API.

An agenda names people, so a signal's summary never quotes an item. It says which body, which
meeting, which item and which words.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

from collectors.tx.legistar import Client, event_url, reduce_event
from pipeline.signals import Doc, Rules, legistar_agenda, process, read_listings

FIXTURES = Path(__file__).parent / "fixtures"
LIST = (FIXTURES / "tx_comptroller_data_centers" / "data-center-lists.html").read_bytes()
RULES = Rules(listings=read_listings(LIST), listings_sha256=hashlib.sha256(LIST).hexdigest())
HARRIS = Client("harriscountytx", "Harris County", ("Harris",))
ROUND_ROCK = Client("roundrock", "Round Rock city", ("Travis",))
WHEN = dt.datetime(2026, 11, 21, 20, 0, tzinfo=dt.UTC)


def saved(name: str) -> dict:
    return json.loads((FIXTURES / "tx_agendas_legistar" / f"{name}.txt").read_bytes())


def agenda_doc(agenda: dict, record: str = "legistar_agenda") -> Doc:
    body = json.dumps(agenda).encode()
    url = event_url(agenda.get("client", "x"), agenda.get("event_id", 0))
    return Doc(
        "tx_agendas_legistar",
        url,
        WHEN,
        hashlib.sha256(body).hexdigest(),
        "",
        {"record": record},
        body,
    )


def harris(**changes) -> dict:
    return {**reduce_event(saved("harris-event-1244-trimmed"), HARRIS), **changes}


def test_a_real_agenda_item_about_data_centers_is_one_signal():
    out = legistar_agenda(agenda_doc(harris()), RULES)
    (draft,) = out.drafts
    assert draft.signal_type == "agenda_keyword"
    assert draft.event_date == dt.date(2026, 10, 15)
    assert draft.county_fips == "48201"  # Harris
    assert draft.party is None and draft.party_kind is None
    assert draft.confidence == 0.9
    assert draft.summary == (
        "The agenda of the Harris County Commissioners Court for October 15, 2026 has an item "
        'that uses the words "data center": item 343, file 26-6897.'
    )
    assert draft.extracted["reference"] == (
        "Harris County Commissioners Court, meeting of October 15, 2026, item 343, file 26-6897"
    )
    assert draft.extracted["page"].startswith("https://harriscountytx.legistar.com/MeetingDetail")
    assert draft.extracted["reasons"] == [
        {"rule": "direct_term", "term": "data center", "field": "title", "text": "data center"}
    ]
    assert any("data center development" in s for s in draft.extracted["snippets"])
    # Seven items were read. Six gave no reason.
    assert (out.records, out.no_reason) == (7, 6)


def test_the_summary_never_quotes_the_item():
    """An item can name an applicant or an appointee. The summary must not carry that."""
    agenda = harris()
    item = next(i for i in agenda["items"] if i["file"] == "26-6897")
    item["title"] = "Request by Jane Q. Example for a variance for a data center at 1 Example Road."
    (draft,) = legistar_agenda(agenda_doc(agenda), RULES).drafts
    assert "Example" not in draft.summary and "variance" not in draft.summary
    assert "Example" not in draft.extracted["reference"]
    # The reviewer still gets the words around the match.
    assert any("data center" in s for s in draft.extracted["snippets"])


def test_an_agenda_with_no_such_words_gives_no_signal():
    agenda = reduce_event(saved("roundrock-event-3430"), ROUND_ROCK)
    out = legistar_agenda(agenda_doc(agenda), RULES)
    assert out.drafts == []
    assert out.records == out.no_reason == 29


def test_the_same_item_read_twice_is_the_same_signal_and_a_changed_agenda_adds_none():
    first = legistar_agenda(agenda_doc(harris()), RULES).drafts[0]
    again = legistar_agenda(agenda_doc(harris(modified="2026-10-09T00:00:00")), RULES).drafts[0]
    assert first.fingerprint("tx_agendas_legistar") == again.fingerprint("tx_agendas_legistar")
    assert first.key == "legistar:harriscountytx:1244:" + first.key.rsplit(":", 1)[1]


def test_a_code_word_is_a_weaker_reason_than_the_words_themselves():
    agenda = harris()
    agenda["items"] = [
        {
            "id": 1, "sequence": 1, "number": "4.", "file": "26-0001", "type": "Resolution",
            "name": "", "note": "",
            "title": "Consider designating a reinvestment zone for a technology campus.",
        }
    ]  # fmt: skip
    (draft,) = legistar_agenda(agenda_doc(agenda), RULES).drafts
    assert draft.confidence == 0.3
    assert '"reinvestment zone", "technology campus"' in draft.summary
    assert [r["rule"] for r in draft.extracted["reasons"]] == ["code_word", "code_word"]


def test_a_government_outside_the_30_counties_gives_no_signal():
    out = legistar_agenda(agenda_doc(harris(counties=["Williamson"])), RULES)
    assert out.drafts == [] and out.out_of_scope == 1


def test_a_city_in_two_test_counties_is_placed_in_the_first_and_both_are_kept():
    (draft,) = legistar_agenda(agenda_doc(harris(counties=["Dallas", "Ellis"])), RULES).drafts
    assert draft.county_fips == "48113"
    assert draft.extracted["counties"] == ["Dallas", "Ellis"]


def test_the_list_of_meetings_itself_is_not_read_for_signals():
    listing = {"platform": "legistar", "client": "harriscountytx", "meetings": []}
    out = process(agenda_doc(listing, record="legistar_meetings"), RULES)
    assert out.drafts == [] and out.records == 0


def test_an_item_with_no_number_is_still_named():
    agenda = harris()
    item = next(i for i in agenda["items"] if i["file"] == "26-6897")
    item["number"], item["file"] = "", ""
    (draft,) = legistar_agenda(agenda_doc(agenda), RULES).drafts
    assert f"item in position {item['sequence']}" in draft.summary


def test_project_followed_by_an_ordinary_word_is_not_a_code_name():
    """Seen in real agendas on the first live run: funding lines and report headings."""
    agenda = harris()
    titles = [
        "Request for approval of the FY26 Community Project Funding for the county.",
        "City Manager Reports, Project Updates, Future Agendas and Direction.",
        "Abandonment as part of Project Group 24-3002, list attached.",
    ]
    agenda["items"] = [
        {"id": n, "sequence": n, "number": f"{n}.", "file": "", "type": "", "name": "",
         "note": "", "title": title}
        for n, title in enumerate(titles, start=1)
    ]  # fmt: skip
    out = legistar_agenda(agenda_doc(agenda), RULES)
    assert out.drafts == [] and out.no_reason == 3
    # A real code name still counts.
    agenda["items"][0]["title"] = "Public hearing on a performance agreement for Project Charge."
    (draft,) = legistar_agenda(agenda_doc(agenda), RULES).drafts
    assert draft.extracted["reasons"][0]["term"] == "Project Charge"
