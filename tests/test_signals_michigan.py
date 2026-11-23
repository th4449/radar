"""Agenda signals for a second state. BUILD_PLAN.md milestone M11.

The two agenda processors are shared. The state comes from the source a document was stored
under, so a Michigan agenda is placed in a Michigan county and never in a Texas one.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json

import pytest

from pipeline.signals import PROCESSORS, Doc, Rules, agenda_file, legistar_agenda, place_name

RULES = Rules(listings={}, listings_sha256="")
WHEN = dt.datetime(2026, 11, 23, 20, 0, tzinfo=dt.UTC)
PAGE = "https://www.example-twp.org/agendas"


def meeting(**changes) -> dict:
    base = {
        "client": "example",
        "event_id": 77,
        "government": "Washtenaw County",
        "body": "Board of Commissioners",
        "counties": ["Washtenaw"],
        "date": "2026-11-04",
        "page": "https://example.legistar.com/MeetingDetail.aspx?ID=77",
        "items": [
            {
                "id": 9001,
                "number": "7.",
                "sequence": 7,
                "title": "Discussion of a moratorium on data center development",
                "note": "",
                "file": "",
                "type": "",
            }
        ],
    }
    return {**base, **changes}


def legistar_doc(agenda: dict, source: str = "mi_agendas_legistar") -> Doc:
    body = json.dumps(agenda).encode()
    return Doc(
        source,
        f"https://webapi.legistar.com/v1/{agenda['client']}/events/{agenda['event_id']}",
        WHEN,
        hashlib.sha256(body).hexdigest(),
        "",
        {"record": "legistar_agenda"},
        body,
    )


def file_doc(text: str, source: str = "mi_agendas_own_sites", **changes) -> Doc:
    facts = {
        "record": "agenda_file",
        "government": "Augusta charter township",
        "counties": ["Washtenaw"],
        "bodies": ["Augusta Charter Township Board of Trustees"],
        "page": PAGE,
        "link_text": "November 10, 2026 Regular Meeting",
        "meeting_date": "2026-11-10",
        "date_from": "link_text",
        **changes,
    }
    return Doc(
        source,
        "https://www.example-twp.org/files/agenda-2026-11-10.pdf",
        WHEN,
        hashlib.sha256(text.encode()).hexdigest(),
        text,
        facts,
        b"%PDF",
    )


AGENDA = (
    "AUGUSTA CHARTER TOWNSHIP BOARD OF TRUSTEES\nREGULAR MEETING AGENDA\nNovember 10, 2026\n\n"
    "1. Call to order\n\n"
    "6. Public hearing on a zoning amendment for a proposed data center on Example Road\n\n"
    "7. Adjournment"
)


def test_both_michigan_agenda_sources_have_a_processor():
    assert PROCESSORS["mi_agendas_legistar"] is legistar_agenda
    assert PROCESSORS["mi_agendas_own_sites"] is agenda_file


def test_a_michigan_item_is_placed_in_a_michigan_county():
    out = legistar_agenda(legistar_doc(meeting()), RULES)
    (draft,) = out.drafts
    assert draft.county_fips == out.county_fips == "26161"
    assert draft.summary == (
        "The agenda of the Washtenaw County Board of Commissioners for November 4, 2026 has "
        'an item that uses the words "data center": item 7.'
    )
    assert draft.extracted["meeting"] == "Washtenaw County, meeting of November 4, 2026"


def test_the_state_comes_from_the_source_and_not_from_the_county_name():
    # Washtenaw is no Texas county. The same record under the Texas source is out of scope.
    out = legistar_agenda(legistar_doc(meeting(), source="tx_agendas_legistar"), RULES)
    assert out.drafts == [] and out.out_of_scope == 1
    # And a Texas county is not looked for in Michigan.
    out = legistar_agenda(legistar_doc(meeting(counties=["Harris"])), RULES)
    assert out.drafts == [] and out.out_of_scope == 1


def test_a_michigan_county_whose_agendas_are_not_read_yet_is_still_a_michigan_county():
    # The radar's Michigan scope is the whole state. The inventory covers six counties.
    (draft,) = legistar_agenda(legistar_doc(meeting(counties=["Ingham"])), RULES).drafts
    assert draft.county_fips == "26065"


@pytest.mark.parametrize(
    ("government", "place"),
    [
        ("Saline city", "Saline"),
        ("Manchester village", "Manchester"),
        ("Washtenaw County", "Washtenaw County"),
        # A township is named with its kind: Ann Arbor is a city and a township.
        ("Ann Arbor charter township", "Ann Arbor Charter Township"),
        ("Lodi township", "Lodi Township"),
        ("Salem township (Washtenaw County)", "Salem Township"),
        ("Round Rock city", "Round Rock"),
    ],
)
def test_a_government_is_named_as_people_say_it(government, place):
    assert place_name(government) == place


def test_a_township_board_is_named_with_its_township():
    agenda = meeting(government="Ann Arbor charter township", body="Board of Trustees")
    (draft,) = legistar_agenda(legistar_doc(agenda), RULES).drafts
    assert "the Ann Arbor Charter Township Board of Trustees" in draft.summary
    assert draft.extracted["meeting"] == ("Ann Arbor Charter Township, meeting of November 4, 2026")


def test_a_michigan_agenda_file_is_one_signal_in_its_county():
    out = agenda_file(file_doc(AGENDA), RULES)
    (draft,) = out.drafts
    assert draft.county_fips == "26161"
    assert draft.summary == (
        "An agenda that Augusta Charter Township posted for a meeting of November 10, 2026 "
        'uses the words "data center".'
    )
    assert draft.extracted["meeting"] == ("Augusta Charter Township, meeting of November 10, 2026")


def test_a_city_in_two_of_the_counties_is_placed_in_the_first():
    doc = file_doc(AGENDA, government="Milan city", counties=["Monroe", "Washtenaw"])
    (draft,) = agenda_file(doc, RULES).drafts
    assert draft.county_fips == "26115"
    assert draft.extracted["counties"] == ["Monroe", "Washtenaw"]


def test_a_source_from_no_state_the_radar_reads_is_refused():
    with pytest.raises(ValueError, match="oh_agendas_legistar"):
        legistar_agenda(legistar_doc(meeting(), source="oh_agendas_legistar"), RULES)
