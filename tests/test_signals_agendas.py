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


def test_a_code_name_counts_only_where_the_item_speaks_of_economic_development_negotiations():
    """The backtest of November 23, 2026: 399 signals rested on "Project" and a code name and
    three were tied to a known project. The rest were phrases such as a project specific
    agreement or a flood control project number. The owner approved the rule agenda files
    already had. A real closed-session item reads as the first title here."""
    agenda = harris()
    titles = [
        "Council may convene into closed Executive Session pursuant to Section 551.087 of the "
        "Texas Government Code to discuss economic development incentives for Project Charge.",
        "Authorize a Project Specific Agreement for the mill and overlay of various streets.",
        "Approve an interlocal agreement for Project Brays, flood control unit D100-00-00.",
    ]
    agenda["items"] = [
        {"id": n, "sequence": n, "number": f"{n}.", "file": "", "type": "", "name": "",
         "note": "", "title": title}
        for n, title in enumerate(titles, start=1)
    ]  # fmt: skip
    out = legistar_agenda(agenda_doc(agenda), RULES)
    (draft,) = out.drafts
    assert [r["term"] for r in draft.extracted["reasons"]] == ["Project Charge"]
    assert out.no_reason == 2


def test_a_code_name_beside_another_term_does_not_ride_along():
    agenda = harris()
    agenda["items"] = [
        {"id": 1, "sequence": 1, "number": "1.", "file": "", "type": "", "name": "", "note": "",
         "title": "Development agreement for the Project Specific paving of Main Street."}
    ]  # fmt: skip
    (draft,) = legistar_agenda(agenda_doc(agenda), RULES).drafts
    assert [r["rule"] for r in draft.extracted["reasons"]] == ["code_word"]
    assert draft.confidence == RULES.confidence["code_word"]


def test_an_item_that_says_data_center_is_held_to_its_government_and_meeting():
    """So it can sit on a site and reach a reviewer. A code word alone opens no site."""
    agenda = harris()
    agenda["items"] = [
        {"id": 1, "sequence": 1, "number": "1.", "file": "", "type": "", "name": "", "note": "",
         "title": "Discussion of data center development in the county."},
        {"id": 2, "sequence": 2, "number": "2.", "file": "", "type": "", "name": "", "note": "",
         "title": "Appointment to the board of a reinvestment zone."},
    ]  # fmt: skip
    direct, weak = legistar_agenda(agenda_doc(agenda), RULES).drafts
    day = dt.date.fromisoformat(agenda["date"])
    assert (
        direct.extracted["meeting"] == f"Harris County, meeting of {day:%B} {day.day}, {day.year}"
    )
    assert weak.extracted["meeting"] is None


# --- a government's own computers ----------------------------------------------------------------


def _items(*titles: str) -> list[dict]:
    return [
        {"id": n, "sequence": n, "number": f"{n}.", "file": "", "type": "", "name": "",
         "note": "", "title": title}
        for n, title in enumerate(titles, start=1)
    ]  # fmt: skip


def test_an_item_about_the_governments_own_computers_is_set_aside():
    """The owner's decision of November 23, 2026. A county renewing its hosting contract uses
    the words "data center" and is not a signal."""
    agenda = harris()
    agenda["items"] = _items(
        "Request for approval of a renewal option with Example Hosting, LLC for data center "
        "co-location and network services for the county, at a cost of $1,500,000.",
        "Discussion of data center development in the county and the county's authority.",
    )
    out = legistar_agenda(agenda_doc(agenda), RULES)
    (kept,) = out.drafts
    assert kept.extracted["item"]["number"] == "2."
    assert out.own_computers == 1 and out.no_reason == 0
    assert out.counts()["own_computers"] == 1


def test_an_item_set_aside_still_counts_for_another_term_it_uses_and_opens_no_site():
    agenda = harris()
    agenda["items"] = _items(
        "Purchase of data center services and data processing equipment for the Information "
        "Technology Department."
    )
    (draft,) = legistar_agenda(agenda_doc(agenda), RULES).drafts
    assert [r["rule"] for r in draft.extracted["reasons"]] == ["code_word"]
    assert draft.confidence == RULES.confidence["code_word"]
    assert draft.extracted["meeting"] is None
    assert draft.extracted["set_aside"] == {
        "rule": "own_computers",
        "shows": "information technology",
    }


def test_an_item_about_a_project_is_kept_even_when_it_names_computing_services():
    agenda = harris()
    agenda["items"] = _items(
        "Tax abatement agreement with Example LLC for a data center offering co-location."
    )
    out = legistar_agenda(agenda_doc(agenda), RULES)
    (draft,) = out.drafts
    assert draft.confidence == RULES.confidence["direct_term"]
    assert out.own_computers == 0


# --- a term that is not a reason by itself --------------------------------------------------------


def test_an_item_that_says_only_special_land_use_is_no_signal():
    """The owner's decision of November 24, 2026."""
    agenda = harris()
    agenda["items"] = _items(
        "Public hearing on a special land use request for a drive-through at 12 Main Street.",
        "Zoning amendment to make data centers a special land use in the overlay district.",
        # A code name that does not count leaves the term alone, and so no reason.
        "Special land use for Project Falcon.",
    )
    out = legistar_agenda(agenda_doc(agenda), RULES)
    (kept,) = out.drafts
    assert kept.extracted["item"]["number"] == "2."
    assert {r["term"] for r in kept.extracted["reasons"]} == {"special land use", "data center"}
    assert (out.records, out.no_reason) == (3, 2)


# --- a government writing its own rules -----------------------------------------------------------


def test_an_item_that_says_data_center_beside_moratorium_is_labelled_for_the_reviewer():
    """The owner's decision of November 24, 2026. The label changes nothing else."""
    agenda = harris()
    agenda["items"] = _items(
        "Public hearing on Ordinance 313, a 12-month moratorium on data centers.",
        "Discussion of data center development in the county and the county's authority.",
    )
    first, second = legistar_agenda(agenda_doc(agenda), RULES).drafts
    assert first.extracted["rule_making"] == {"words": ["moratorium", "ordinance"]}
    assert "rule_making" not in second.extracted
    assert first.confidence == second.confidence
    assert "moratorium" not in first.summary
