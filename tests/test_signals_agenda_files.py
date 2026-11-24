"""Agenda files from governments' own sites become signals.

The files here are made up. A real agenda names people, and so can its file name, so a signal's
summary names the government, the date and the words that matched, and nothing else.
"""

from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path

import pytest

from pipeline.signals import PROCESSORS, Doc, Rules, agenda_file, process, read_listings

FIXTURES = Path(__file__).parent / "fixtures"
LIST = (FIXTURES / "tx_comptroller_data_centers" / "data-center-lists.html").read_bytes()
RULES = Rules(listings=read_listings(LIST), listings_sha256=hashlib.sha256(LIST).hexdigest())
WHEN = dt.datetime(2026, 11, 21, 20, 0, tzinfo=dt.UTC)
URL = "https://www.example.gov/files/AGENDA%2011.17.26%20ATTY%20SMITH.pdf?t=202611101701550"
PAGE = "https://www.example.gov/government/agendas"

HEAD = "CITY OF EXAMPLE\nNOTICE OF MEETING AND AGENDA\nTuesday, November 17, 2026 at 6:00 p.m."
ROUTINE = "1. Call to order.\n2. Approve the minutes of the last meeting.\n3. Pay the bills."
ZONE = "4. Public hearing on designating a reinvestment zone on County Road 12."
CENTER = "5. Presentation by staff on a proposed data center and its water use."


def facts(**changes) -> dict:
    base = {
        "record": "agenda_file",
        "government": "Sealy city",
        "counties": ["Austin"],
        "bodies": ["Sealy City Council", "Sealy Planning Commission"],
        "page": PAGE,
        "link_text": "November 17, 2026 Regular Meeting",
        "meeting_date": "2026-11-17",
        "date_from": "link_text",
    }
    return {**base, **changes}


def doc(*pages: str, url: str = URL, **changes) -> Doc:
    text = "\n\n".join(pages)
    return Doc(
        "tx_agendas_own_sites",
        url,
        WHEN,
        hashlib.sha256(text.encode()).hexdigest(),
        text,
        facts(**changes),
        b"%PDF",
    )


def test_an_agenda_that_uses_a_term_is_one_signal():
    out = agenda_file(doc(HEAD, ROUTINE, ZONE + "\n" + CENTER), RULES)
    assert out.counts() == {
        "records": 1, "signals": 1, "no_reason": 0, "held_back": 0, "out_of_scope": 0,
        "undated": 0,
    }  # fmt: skip
    (draft,) = out.drafts
    assert draft.signal_type == "agenda_keyword"
    assert draft.event_date == dt.date(2026, 11, 17)
    assert draft.county_fips == "48015" == out.county_fips  # Austin County
    assert draft.party is None and draft.party_kind is None
    assert draft.summary == (
        "An agenda that Sealy posted for a meeting of November 17, 2026 uses the words "
        '"reinvestment zone", "data center".'
    )
    assert draft.extracted["reference"] == "Sealy, agenda for the meeting of November 17, 2026"
    assert draft.extracted["page"] == PAGE
    assert draft.extracted["pages_with_terms"] == [3]
    assert draft.extracted["date_from"] == "link_text"
    assert draft.extracted["bodies_on_page"] == ["Sealy City Council", "Sealy Planning Commission"]
    assert {r["term"] for r in draft.extracted["reasons"]} == {"reinvestment zone", "data center"}
    assert any("data center" in s for s in draft.extracted["snippets"])


def test_the_summary_never_carries_the_file_name_the_link_text_or_the_items_words():
    """The file here is named for a person. Nothing a reader of the alert sees repeats it."""
    (draft,) = agenda_file(doc(HEAD, ZONE), RULES).drafts
    public = draft.summary + " " + draft.extracted["reference"]
    assert "SMITH" not in public.upper() and "County Road" not in public
    assert "Regular Meeting" not in public and ".pdf" not in public


def test_one_file_is_one_signal_however_many_pages_use_a_term():
    out = agenda_file(doc(HEAD + "\n" + ZONE, ROUTINE, CENTER, ZONE), RULES)
    (draft,) = out.drafts
    assert draft.extracted["pages_with_terms"] == [1, 3, 4]
    assert len(draft.extracted["reasons"]) == 2


def test_the_same_file_under_a_new_address_stamp_is_the_same_signal():
    first = agenda_file(doc(HEAD, ZONE), RULES).drafts[0]
    again = agenda_file(doc(HEAD, ZONE, url=URL.split("?")[0] + "?t=202611181200000"), RULES)
    other = agenda_file(doc(HEAD, ZONE, url="https://www.example.gov/files/b.pdf"), RULES)
    source = "tx_agendas_own_sites"
    assert first.fingerprint(source) == again.drafts[0].fingerprint(source)
    assert first.fingerprint(source) != other.drafts[0].fingerprint(source)


def test_an_agenda_with_no_term_is_no_signal():
    out = agenda_file(doc(HEAD, ROUTINE), RULES)
    assert out.drafts == [] and (out.records, out.no_reason) == (1, 1)


def test_minutes_posted_among_the_agendas_are_not_called_an_agenda():
    minutes = "CITY OF EXAMPLE\nMINUTES OF THE REGULAR MEETING\nNovember 3, 2026"
    out = agenda_file(doc(minutes, ZONE), RULES)
    assert out.drafts == [] and out.no_reason == 1
    # An agenda that has an item about the minutes is still an agenda.
    assert len(agenda_file(doc(HEAD, ROUTINE + "\n" + ZONE), RULES).drafts) == 1


def test_a_scanned_file_with_no_text_is_counted_as_unread_not_as_clean():
    out = agenda_file(doc(""), RULES)
    assert out.drafts == [] and out.no_text == 1 and out.no_reason == 0
    assert out.counts()["no_text"] == 1


def test_a_file_the_page_did_not_date_takes_the_date_at_its_own_head():
    out = agenda_file(doc(HEAD, ZONE, meeting_date=None, date_from=None), RULES)
    (draft,) = out.drafts
    assert draft.event_date == dt.date(2026, 11, 17)
    assert draft.extracted["date_from"] == "file_text"


def test_a_file_with_no_date_anywhere_is_held_as_undated():
    head = "CITY OF EXAMPLE\nNOTICE OF MEETING AND AGENDA"
    out = agenda_file(doc(head, ZONE, meeting_date=None, date_from=None), RULES)
    assert out.drafts == [] and out.undated == 1


def test_a_government_outside_the_test_counties_gives_no_signal():
    out = agenda_file(doc(HEAD, ZONE, government="Mentone town", counties=["Loving"]), RULES)
    assert out.drafts == [] and out.out_of_scope == 1


def test_a_county_government_is_named_as_it_is():
    (draft,) = agenda_file(doc(HEAD, ZONE, government="Austin County"), RULES).drafts
    assert draft.summary.startswith("An agenda that Austin County posted for a meeting of ")


def test_the_list_of_links_on_a_page_is_not_read_for_signals():
    listing = Doc(
        "tx_agendas_own_sites", PAGE, WHEN, "0" * 64, ZONE, {"record": "agenda_page"}, b""
    )
    out = agenda_file(listing, RULES)
    assert out.drafts == [] and out.records == 0


def test_the_processor_is_registered_for_the_source():
    assert PROCESSORS["tx_agendas_own_sites"] is agenda_file
    assert len(process(doc(HEAD, ZONE), RULES).drafts) == 1


def test_a_code_name_counts_only_where_the_agenda_speaks_of_economic_development():
    """A real packet gave "Project Documentation" and "Project Per the schedule". A real agenda
    gave a code name under its closed session on economic development negotiations."""
    works = "6. Memorial Drive Signal Rebuilds Project Per the schedule, work began in October."
    out = agenda_file(doc(HEAD, works + "\nProject Documentation: exhibits were provided."), RULES)
    assert out.drafts == [] and out.no_reason == 1

    closed = (
        "11. Closed session under Section 551.087 to deliberate economic development "
        "negotiations.\n i. Project Falcon"
    )
    (draft,) = agenda_file(doc(HEAD, closed), RULES).drafts
    assert [r["text"] for r in draft.extracted["reasons"]] == ["Project Falcon"]
    # The name is not a reason when a line break splits it or the words are far off.
    assert (
        agenda_file(doc(HEAD, "Economic development.\nRoad Project\nFalcon Lane"), RULES).drafts
        == []
    )


def test_a_signal_from_a_scan_says_a_machine_read_it():
    read = {
        "engine": "tesseract 5.5.4", "dpi": 300, "pages_read": 2, "pages_in_file": 2,
        "words": 310, "confidence": 94.2, "doubtful_words": 6,
    }  # fmt: skip
    (draft,) = process(doc(HEAD, ZONE, ocr=read), RULES).drafts
    assert draft.summary == (
        "An agenda that Sealy posted for a meeting of November 17, 2026 uses the words "
        '"reinvestment zone". The file is a scan, read by character recognition.'
    )
    assert draft.extracted["text_from"] == "ocr"
    assert draft.extracted["ocr"] == {
        "engine": "tesseract 5.5.4", "confidence": 94.2, "doubtful_words": 6, "words": 310,
        "pages_read": 2, "pages_in_file": 2,
    }  # fmt: skip
    # A file with its own text says nothing of the kind.
    (plain,) = process(doc(HEAD, ZONE), RULES).drafts
    assert "scan" not in plain.summary and "text_from" not in plain.extracted
    # The same fact is the same signal, read by machine or not.
    source = "tx_agendas_own_sites"
    assert draft.fingerprint(source) == plain.fingerprint(source)


def test_a_file_that_says_data_center_is_held_to_its_government_and_meeting():
    (direct,) = agenda_file(doc(HEAD, ROUTINE, CENTER), RULES).drafts
    assert direct.extracted["meeting"] == "Sealy, meeting of November 17, 2026"
    (weak,) = agenda_file(doc(HEAD, ROUTINE, ZONE), RULES).drafts
    assert weak.extracted["meeting"] is None


# --- a government's own computers ----------------------------------------------------------------

REFRESH = (
    "19. Ordinance appropriating $850,000 out of the Equipment Fund for the planned Data Center "
    "Refresh Project for Information Technology Services."
)
BOARD = "20. Ordinance appointing a member to the board of Reinvestment Zone Number Seven."


def test_a_file_whose_only_use_of_the_words_is_the_governments_own_computers_is_no_signal():
    out = agenda_file(doc(HEAD, ROUTINE + "\n" + REFRESH), RULES)
    assert out.drafts == []
    assert out.own_computers == 1 and out.no_reason == 0


def test_only_the_item_itself_decides_and_not_the_item_beside_it():
    # The next item names a reinvestment zone. That is another matter and does not make the
    # hosting item a project. The file still gives its weaker signal for the zone.
    (draft,) = agenda_file(doc(HEAD, REFRESH + "\n" + BOARD), RULES).drafts
    assert [r["term"] for r in draft.extracted["reasons"]] == ["reinvestment zone"]
    assert draft.extracted["meeting"] is None
    assert draft.extracted["set_aside"]["rule"] == "own_computers"


def test_a_file_with_a_project_item_and_a_hosting_item_keeps_the_project():
    (draft,) = agenda_file(doc(HEAD, REFRESH + "\n" + CENTER), RULES).drafts
    assert [r["rule"] for r in draft.extracted["reasons"]] == ["direct_term"]
    assert draft.extracted["meeting"] == "Sealy, meeting of November 17, 2026"


# --- a term that is not a reason by itself --------------------------------------------------------

DRIVE_THROUGH = "4. Public hearing on a special land use request for a drive-through at 12 Main."
OVERLAY = "5. Zoning amendment to make data centers a special land use in the overlay district."


def test_special_land_use_alone_is_no_signal():
    """The owner's decision of November 24, 2026, after it was tried on 56 Michigan agendas."""
    out = agenda_file(doc(HEAD, ROUTINE, DRIVE_THROUGH), RULES)
    assert out.drafts == []
    assert (out.records, out.no_reason) == (1, 1)


def test_special_land_use_still_counts_beside_another_term_in_the_same_file():
    (draft,) = agenda_file(doc(HEAD, ROUTINE, DRIVE_THROUGH, OVERLAY), RULES).drafts
    assert {r["term"] for r in draft.extracted["reasons"]} == {"special land use", "data center"}
    assert draft.extracted["pages_with_terms"] == [3, 4]
    # Beside another code word too, on another page of the same file.
    (draft,) = agenda_file(doc(HEAD, DRIVE_THROUGH, ZONE), RULES).drafts
    assert {r["term"] for r in draft.extracted["reasons"]} == {
        "special land use",
        "reinvestment zone",
    }


# --- a government writing its own rules -----------------------------------------------------------

MORATORIUM = "10. First reading of a general moratorium ordinance on data centers."
STORAGE = "11. First reading of a general moratorium ordinance on energy storage."


def test_a_reviewer_is_told_when_data_center_sits_beside_the_words_of_rule_making():
    """The owner's decision of November 24, 2026.

    On 56 real Michigan agendas, 11 of the 15 files that said "data center" were a moratorium or
    a zoning ordinance. The label says which words sit in the same item. It changes nothing
    else: the record is a signal as before, with the same summary and the same confidence.
    """
    plain = agenda_file(doc(HEAD, ROUTINE, CENTER), RULES).drafts[0]
    (draft,) = agenda_file(doc(HEAD, ROUTINE, MORATORIUM), RULES).drafts
    assert draft.extracted["rule_making"] == {"words": ["moratorium", "ordinance"]}
    assert "rule_making" not in plain.extracted
    assert draft.confidence == plain.confidence
    assert draft.summary == plain.summary
    assert "moratorium" not in draft.summary


def test_the_label_looks_only_at_the_item_that_says_data_center():
    # The moratorium is on something else, in the next item.
    (draft,) = agenda_file(doc(HEAD, ROUTINE, CENTER + "\n" + STORAGE), RULES).drafts
    assert "rule_making" not in draft.extracted
    # A code word beside "ordinance" is not labelled: the label is for the words themselves.
    (draft,) = agenda_file(
        doc(HEAD, "4. An ordinance designating a reinvestment zone on County Road 12."), RULES
    ).drafts
    assert "rule_making" not in draft.extracted


DEFINITION = (
    "SECTION II DEFINITIONS\n"
    "1. Data Center: A facility used for centralized storage, management, processing, and "
    "transmission of digital information, typically containing computer servers and data "
    "storage systems.\n"
    "2. Applicant: A person who files a request under this section."
)


def test_a_file_that_holds_only_an_ordinances_definition_of_a_data_center_is_a_signal():
    """Before November 24, 2026 the definition was set aside for its word "servers", and a file
    that held nothing else about data centers gave no signal."""
    out = agenda_file(doc(HEAD, ROUTINE, DEFINITION), RULES)
    (draft,) = out.drafts
    assert out.own_computers == 0
    assert [r["term"] for r in draft.extracted["reasons"]] == ["data center"]
    assert "set_aside" not in draft.extracted


# --- a long file, with the words past its first page ----------------------------------------------

BILLS = "CHECK REGISTER\n29853 EXAMPLE EQUITIES - DATA CENTER escrow refund 6,000.00"
LONG = "\n\n".join(["Minutes of the last meeting, continued."] * 4)


def test_a_long_file_with_the_words_past_its_first_page_is_not_called_an_agenda():
    """A packet binds the agenda to the minutes of earlier meetings and to lists of bills.

    On 56 real Michigan agendas, three of the 15 files that said "data center" said it there
    and nowhere on the agenda. The summary called each an agenda for that day's meeting. Now it
    says what the record shows: a file of so many pages, with the words past its first page.
    """
    (draft,) = agenda_file(doc(HEAD, ROUTINE, LONG, BILLS, pages=31), RULES).drafts
    assert draft.summary == (
        "A 31-page file that Sealy posted for a meeting of November 17, 2026 uses the words "
        '"data center" past its first page.'
    )
    assert draft.extracted["reference"] == "Sealy, file posted for the meeting of November 17, 2026"
    assert draft.extracted["past_first_page"] is True
    assert draft.extracted["file_pages"] == 31
    # The same record is a signal, as sure as before and held to the same meeting.
    (plain,) = agenda_file(doc(HEAD, ROUTINE, LONG, BILLS), RULES).drafts
    assert (draft.confidence, draft.key, draft.event_date) == (
        plain.confidence,
        plain.key,
        plain.event_date,
    )
    assert draft.extracted["meeting"] == plain.extracted["meeting"]


def test_a_long_file_with_the_words_on_its_first_page_is_an_agenda_as_before():
    first = HEAD + "\n10. First reading of a general moratorium ordinance on data centers."
    (draft,) = agenda_file(doc(first, LONG, BILLS, pages=52), RULES).drafts
    assert draft.summary.startswith("An agenda that Sealy posted for a meeting of ")
    assert "past_first_page" not in draft.extracted
    assert draft.extracted["reference"] == "Sealy, agenda for the meeting of November 17, 2026"


def test_a_file_of_one_or_two_pages_is_an_agenda_wherever_the_words_are():
    (draft,) = agenda_file(doc(HEAD + "\n" + ROUTINE, CENTER, pages=2), RULES).drafts
    assert draft.summary.startswith("An agenda that Sealy posted for a meeting of ")
    # A file whose pages were not counted reads as it did.
    (draft,) = agenda_file(doc(HEAD, ROUTINE, CENTER), RULES).drafts
    assert draft.summary.startswith("An agenda that Sealy posted for a meeting of ")
    (draft,) = agenda_file(doc(HEAD, ROUTINE, CENTER, pages=None), RULES).drafts
    assert draft.summary.startswith("An agenda that Sealy posted for a meeting of ")


@pytest.mark.parametrize(
    ("pages", "start"),
    [(3, "A 3-page"), (8, "An 8-page"), (11, "An 11-page"), (18, "An 18-page"),
     (80, "An 80-page"), (110, "A 110-page"), (260, "A 260-page"), (800, "An 800-page")],
)  # fmt: skip
def test_the_count_of_pages_reads_as_a_person_would_say_it(pages, start):
    (draft,) = agenda_file(doc(HEAD, ROUTINE, LONG, BILLS, pages=pages), RULES).drafts
    assert draft.summary.startswith(start + " file that Sealy posted for a meeting of ")


def test_a_long_scanned_file_still_says_a_machine_read_it():
    read = {"engine": "tesseract 5.5.4", "confidence": 94.2, "doubtful_words": 6, "words": 310}
    (draft,) = process(doc(HEAD, ROUTINE, LONG, BILLS, pages=31, ocr=read), RULES).drafts
    assert draft.summary == (
        "A 31-page file that Sealy posted for a meeting of November 17, 2026 uses the words "
        '"data center" past its first page. The file is a scan, read by character recognition.'
    )
