"""Agenda files that governments post on their own sites.

The page fixtures are real pages, saved on November 21, 2026 and cut down to the part that
lists agendas. Each fixture's .meta.json says so. The agenda files in these tests are made up:
a real agenda names people.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import httpx
import pytest

from collectors.base import Fetcher, LocalArchive
from collectors.tx.agenda_pages import (
    AgendaPages,
    Page,
    cleared_pages,
    dates_in,
    find_agenda_links,
    find_date,
    on_the_site,
)
from pipeline.config import load_sources
from pipeline.store import MemorySink

from .helpers import CONTACT, FakeClock, Site, make_pdf

FIXTURES = Path(__file__).parent / "fixtures" / "tx_agendas_own_sites"
TODAY = dt.date(2026, 11, 21)


def saved(name: str) -> tuple[bytes, str]:
    meta = json.loads((FIXTURES / f"{name}.meta.json").read_text())
    return (FIXTURES / f"{name}.html").read_bytes(), meta["final_url"]


def links(name: str):
    body, url = saved(name)
    return find_agenda_links(body, url, TODAY)


def source():
    return next(s for s in load_sources().sources if s.id == "tx_agendas_own_sites")


# --- reading a date ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("written", "day"),
    [
        ("November 17, 2026", "2026-11-17"),
        ("SEDC Agenda Oct. 27, 2026 Final.pdf", "2026-10-27"),
        ("Nov-03-2026-Agenda-1.docx", "2026-11-03"),
        ("November_12_2026_City_Council_Meeting-_Agenda.pdf", "2026-11-12"),
        ("Agenda2026November10CouncilMeeting.pdf", "2026-11-10"),
        ("Oct1326.pdf", "2026-10-13"),
        ("2026-11-17  Agenda.pdf", "2026-11-17"),
        ("11.23.26.pdf", "2026-11-23"),
        ("AGENDA 11 2 2026.docx", "2026-11-02"),
        ("CC-SM-Agenda-11.16.26-Amended.pdf", "2026-11-16"),
    ],
)
def test_a_date_written_out_is_read(written, day):
    assert str(find_date(written, TODAY)) == day


@pytest.mark.parametrize(
    ("name", "day"),
    [
        ("Agenda_11192026.pdf", "2026-11-19"),
        ("20261117.pdf", "2026-11-17"),
        ("111626__Agenda.pdf", "2026-11-16"),
        ("261123 - Council Agenda Posted.pdf", "2026-11-23"),
        ("Agenda_8272026.pdf", "2026-08-27"),
        ("Agenda_72326.pdf", "2026-07-23"),
    ],
)
def test_digits_run_together_are_read_only_when_asked_and_only_one_way(name, day):
    assert find_date(name, TODAY) is None
    assert str(find_date(name, TODAY, runs=True)) == day


@pytest.mark.parametrize(
    "name",
    [
        "1122026.pdf",  # January 12 or November 2
        "Council Agenda Nov26.pdf",  # a month and a year, no day
        "SKM_C450i26102816540.pdf",  # a copier's serial number
        "nav-30-6b00b8c6913e6.pdf",
        "AGENDA-1.pdf",
        "Suite 100 12 2026",
        "Mayor 5 2026 letter.pdf",
        "Agenda 13-45-2026.pdf",
    ],
)
def test_a_date_that_is_not_sure_is_no_date(name):
    assert find_date(name, TODAY, runs=True) is None


def test_a_date_far_from_today_is_a_number_not_a_meeting():
    assert find_date("Agenda 01-05-2009.pdf", TODAY) is None
    assert find_date("Agenda 01-05-2031.pdf", TODAY) is None
    assert dates_in("Item 3.4.12 and 11/17/2026 and November 17, 2026", TODAY) == [
        dt.date(2026, 11, 17)
    ]


# --- real pages -----------------------------------------------------------------------------------


def test_a_county_page_that_dates_each_link_in_its_own_words():
    found = links("austin-county")
    assert len(found) == 11
    assert all(link.date_from == "link_text" for link in found)
    first = found[0]
    assert first.url == "https://www.austincounty.com/upload/page/6245/11.23.26.pdf"
    assert (first.text, first.date) == ("November 23, 2026", dt.date(2026, 11, 23))
    # Two meetings on one day are two files.
    assert [link.text for link in found if link.date == dt.date(2026, 9, 14)] == [
        "September 14, 2026 6:00 pm",
        "September 14, 2026 9:00 am",
    ]


def test_links_drawn_as_pictures_are_read_by_their_table_column():
    """Hollywood Park: a table headed Meeting Date, Agenda, Video, Minutes. Each link is an
    icon. Only the Agenda column is taken."""
    body, url = saved("hollywood-park")
    assert body.count(b"minutes") > 5 and b"recording.example" in body
    found = links("hollywood-park")
    assert len(found) == 15
    assert all("/wp-content/uploads/2026/" in link.url for link in found)
    assert not [link for link in found if "minutes" in link.text.lower()]
    # The row says "January 28". The year comes from the folder the file was uploaded to.
    assert (found[0].date, found[0].date_from) == (dt.date(2026, 1, 28), "row_and_upload_folder")
    # The newest row. Its picture's label names another meeting, and is not believed.
    assert found[-1].text == "August 24 Budget Meeting agenda"
    assert (found[-1].date, found[-1].date_from) == (dt.date(2026, 11, 17), "row_and_upload_folder")


def test_a_packet_is_taken_when_it_is_the_only_agenda_and_a_scanners_name_is_not_a_date():
    """Merkel: "11-17-26 Agenda and Packet" leads to DOC110926-11092026150028.pdf, a file named
    for the minute it was scanned, eight days before the meeting."""
    found = links("merkel")
    first = found[0]
    assert first.url.endswith("/DOC110926-11092026150028.pdf")
    assert (first.date, first.date_from) == (dt.date(2026, 11, 17), "link_text")
    assert len(found) == 10 and all(link.date_from == "link_text" for link in found)


def test_quorum_notices_and_minutes_are_left_on_a_page_that_mixes_them():
    body, _ = saved("bruceville-eddy")
    assert body.count(b"Notice of possible quorum") >= 4 and b"Minutes" in body
    found = links("bruceville-eddy")
    assert len(found) == 24
    said = " ".join(link.text for link in found).lower()
    assert "quorum" not in said and "minutes" not in said
    assert found[-1].text == "11-16-2026 Special Called Meeting Agenda"
    # A meeting with no word "agenda" in its link is taken, because the page is about meetings
    # and the link is dated.
    assert "10-30-2025 Special Called City Council Meeting" in [link.text for link in found]


# --- the rules, one at a time ---------------------------------------------------------------------

PAGE = "https://www.example.gov/government/agendas"


def page(inner: str, title: str = "Agendas") -> bytes:
    return f"<html><head><title>{title}</title></head><body>{inner}</body></html>".encode()


def test_a_packet_is_left_when_the_plain_agenda_for_the_day_is_there():
    body = page(
        '<ul><li><a href="/files/2026-11-17-agenda.pdf">Agenda</a></li>'
        '<li><a href="/files/2026-11-17-agenda-packet.pdf">Agenda Packet</a></li>'
        '<li><a href="/files/2026-11-03-agenda-packet.pdf">Agenda Packet</a></li></ul>'
    )
    assert [link.url.rsplit("/", 1)[-1] for link in find_agenda_links(body, PAGE, TODAY)] == [
        "2026-11-17-agenda.pdf",
        "2026-11-03-agenda-packet.pdf",
    ]


def test_minutes_recordings_and_other_files_are_left():
    body = page(
        '<p><a href="/f/11-17-2026-minutes.pdf">11-17-2026</a></p>'
        '<p><a href="/f/a.pdf">Minutes of November 17, 2026</a></p>'
        '<p><a href="/f/b.pdf">Action Taken November 17, 2026</a></p>'
        '<p><a href="/f/budget.pdf">Adopted budget</a></p>'
        '<p><a href="/f/old.doc">Agenda November 17, 2026</a></p>'
        '<p><a href="/meetings/2026-11-17">Agenda November 17, 2026</a></p>'
        '<p><a href="/f/c.pdf">Agenda November 17, 2026</a></p>'
    )
    assert [link.url for link in find_agenda_links(body, PAGE, TODAY)] == [
        "https://www.example.gov/f/c.pdf"
    ]


def test_links_in_the_menu_and_the_footer_are_not_part_of_the_list():
    body = page(
        '<nav><a href="/f/agenda-2026-11-17.pdf">Agenda</a></nav>'
        '<footer><a href="/f/agenda-2026-11-10.pdf">Agenda</a></footer>'
        '<main><a href="/f/agenda-2026-11-03.pdf">Agenda</a></main>'
    )
    assert [link.date for link in find_agenda_links(body, PAGE, TODAY)] == [dt.date(2026, 11, 3)]


def test_a_dated_file_counts_as_an_agenda_only_on_a_page_about_meetings():
    inner = '<p><a href="/f/11-17-2026.pdf">November 17, 2026</a></p>'
    assert len(find_agenda_links(page(inner), PAGE, TODAY)) == 1
    home = "https://www.example.gov/"
    assert find_agenda_links(page(inner, title="City of Example"), home, TODAY) == []
    says = '<p><a href="/f/11-17-2026.pdf">Agenda for November 17, 2026</a></p>'
    assert len(find_agenda_links(page(says, title="City of Example"), home, TODAY)) == 1


def test_a_row_names_the_agenda_only_for_a_link_that_says_nothing_itself():
    body = page(
        '<ul><li>Agenda for the council <a href="/f/x1.pdf">Download</a></li>'
        '<li>Agenda items <a href="/f/x2.pdf">Financial statements</a></li></ul>',
        title="City of Example",
    )
    found = find_agenda_links(body, "https://www.example.gov/", TODAY)
    assert [link.url.rsplit("/", 1)[-1] for link in found] == ["x1.pdf"]


def test_a_row_about_several_meetings_dates_none_of_them():
    body = page(
        "<p>November 3, 2026 and November 17, 2026: "
        '<a href="/f/first-agenda.pdf">Agenda</a> <a href="/f/second-agenda.pdf">Agenda</a></p>'
        '<table><tr><td>November 10, 2026</td><td><a href="/f/third-agenda.pdf">Agenda</a></td>'
        "</tr></table>"
    )
    found = {link.url.rsplit("/", 1)[-1]: link for link in find_agenda_links(body, PAGE, TODAY)}
    assert found["first-agenda.pdf"].date is None and found["second-agenda.pdf"].date is None
    assert (found["third-agenda.pdf"].date, found["third-agenda.pdf"].date_from) == (
        dt.date(2026, 11, 10),
        "row",
    )


def test_a_page_with_no_agenda_files_gives_an_empty_list():
    assert find_agenda_links(page("<p>Agendas are posted at city hall.</p>"), PAGE, TODAY) == []
    assert find_agenda_links(b"", PAGE, TODAY) == []


def test_only_the_governments_own_site_and_its_builders_file_host_count_as_the_site():
    assert on_the_site("https://example.gov/f/a.pdf", "https://www.example.gov/agendas")
    assert on_the_site("https://img1.wsimg.com/blobby/go/x/a.pdf", "https://example.gov/agendas")
    assert not on_the_site("https://files.example.org/a.pdf", "https://www.example.gov/agendas")
    assert not on_the_site("https://docs.example.gov/a.pdf", "https://www.example.gov/agendas")


# --- which pages ----------------------------------------------------------------------------------


def test_the_pages_read_are_the_ones_the_inventory_clears():
    pages = cleared_pages(TODAY)
    governments = {p.government for p in pages}
    assert (len(pages), len(governments)) == (45, 44)
    assert "Austin County" in governments and "Houston city" in governments
    # Closed by a robots file, by its own terms, held for the owner, refused on request, and
    # closed by the robots file of the host that serves its files.
    closed = ("Irving city", "Frankston town", "Austin city", "New Fairview city", "Sealy city")
    assert not governments & set(closed)
    piney = [p for p in pages if p.government == "Piney Point Village city"]
    assert len(piney) == 2 and all(p.counties == ("Harris",) for p in piney)
    assert all(p.url.startswith("http") and p.bodies for p in pages)


# --- a run ----------------------------------------------------------------------------------------

COUNTY_BODY, COUNTY = saved("austin-county")
MERKEL_BODY, MERKEL = saved("merkel")


def agenda(n: int = 0) -> bytes:
    """A made-up agenda. Each file differs, as real ones do."""
    return make_pdf(["AGENDA", f"Item {n + 1}. Consider a tax abatement agreement."])


AGENDA = agenda()
PDF = {"Content-Type": "application/pdf"}
PAGES = (
    Page(COUNTY, "Austin County", ("Austin",), ("Austin County Commissioners Court",)),
    Page(MERKEL, "Merkel town", ("Taylor",), ("Merkel City Council",)),
)
COUNTY_FILES = [
    "https://www.austincounty.com/upload/page/6245/11.23.26.pdf",
    "https://www.austincounty.com/upload/page/6245/11.16.2026.pdf",
    "https://www.austincounty.com/upload/page/6245/11.09.26.pdf",
]
MERKEL_FILES = [
    "https://merkeltexas.com/wp-content/uploads/2026/11/DOC110926-11092026150028.pdf",
    "https://merkeltexas.com/wp-content/uploads/2026/10/DOC102626-10262026082647.pdf",
]


def web() -> Site:
    html = {"Content-Type": "text/html; charset=utf-8"}
    routes = {
        COUNTY: httpx.Response(200, content=COUNTY_BODY, headers=html),
        MERKEL: httpx.Response(200, content=MERKEL_BODY, headers=html),
    }
    for n, url in enumerate(COUNTY_FILES + MERKEL_FILES):
        routes[url] = httpx.Response(200, content=agenda(n), headers=PDF)
    return Site(routes)


def run(site: Site, sink: MemorySink, tmp_path, pages=PAGES):
    clock = FakeClock()
    collector = AgendaPages(pages=pages, today=TODAY)
    with Fetcher(
        source(), contact=CONTACT, transport=site.transport, clock=clock, sleep=clock.sleep
    ) as fetcher:
        return collector.run(
            source=source(), fetcher=fetcher, store=LocalArchive(tmp_path), sink=sink
        )


def test_a_run_reads_each_page_then_its_recent_agenda_files(tmp_path):
    site, sink = web(), MemorySink()
    summary = run(site, sink, tmp_path)
    assert summary.status == "ok", summary.error
    # Both pages first, then the files from the last three weeks, newest first. Older ones stay.
    assert site.page_urls() == [COUNTY, MERKEL, *COUNTY_FILES, *MERKEL_FILES]
    assert (summary.documents_seen, summary.documents_new) == (7, 7)
    assert sink.runs[1]["detail"] == {"governments": 2}
    assert all(r.headers["user-agent"].startswith("DataCenterRadar/") for r in site.requests)


def test_a_page_is_stored_as_its_list_of_agenda_links_and_a_file_as_itself(tmp_path):
    sink = MemorySink()
    run(web(), sink, tmp_path)
    docs = {d.url: d for d in sink.documents.values()}
    listing = json.loads(LocalArchive(tmp_path).get(docs[COUNTY].storage_path))
    assert listing["government"] == "Austin County" and len(listing["agendas"]) == 11
    assert listing["agendas"][0] == {
        "url": COUNTY_FILES[0],
        "text": "November 23, 2026",
        "date": "2026-11-23",
        "date_from": "link_text",
    }
    assert docs[COUNTY].raw_meta["record"] == "agenda_page"
    assert docs[COUNTY].raw_meta["original_kept"] is False

    file = docs[MERKEL_FILES[0]]
    assert LocalArchive(tmp_path).get(file.storage_path) == agenda(3)
    assert "tax abatement" in file.text
    kept = {k: file.raw_meta[k] for k in ("record", "government", "counties", "bodies", "page")}
    assert kept == {
        "record": "agenda_file",
        "government": "Merkel town",
        "counties": ["Taylor"],
        "bodies": ["Merkel City Council"],
        "page": MERKEL,
    }
    assert (file.raw_meta["meeting_date"], file.raw_meta["date_from"]) == (
        "2026-11-17",
        "link_text",
    )


def test_a_second_run_asks_only_for_the_pages(tmp_path):
    sink = MemorySink()
    run(web(), sink, tmp_path)
    again = web()
    summary = run(again, sink, tmp_path)
    assert again.page_urls() == [COUNTY, MERKEL]
    assert (summary.status, summary.documents_new) == ("ok", 0)


def test_a_stored_file_is_asked_for_again_only_when_the_site_can_say_it_is_unchanged(tmp_path):
    sink, first = MemorySink(), web()
    tagged = httpx.Response(200, content=AGENDA, headers={**PDF, "ETag": '"v1"'})
    first.routes[COUNTY_FILES[0]] = tagged
    run(first, sink, tmp_path)

    again = web()
    again.routes[COUNTY_FILES[0]] = lambda request: (
        httpx.Response(304) if request.headers.get("if-none-match") == '"v1"' else tagged
    )
    summary = run(again, sink, tmp_path)
    assert again.page_urls() == [COUNTY, MERKEL, COUNTY_FILES[0]]
    assert (summary.status, summary.documents_new) == ("ok", 0)


def test_at_most_four_files_from_one_page_in_one_run(tmp_path):
    rows = "".join(
        f'<p><a href="/f/agenda-2026-11-{day:02d}.pdf">Agenda</a></p>' for day in range(10, 20)
    )
    site = Site({PAGE: httpx.Response(200, content=page(rows))})
    for day in range(10, 20):
        site.routes[f"https://www.example.gov/f/agenda-2026-11-{day:02d}.pdf"] = httpx.Response(
            200, content=AGENDA, headers=PDF
        )
    run(site, MemorySink(), tmp_path, pages=(Page(PAGE, "Example city", ("Travis",), ("x",)),))
    asked = [u.rsplit("-", 1)[-1] for u in site.page_urls()[1:]]
    assert asked == ["19.pdf", "18.pdf", "17.pdf", "16.pdf"]


def test_a_page_that_dates_nothing_gives_its_first_two_files(tmp_path):
    rows = "".join(f'<p><a href="/f/agenda-{n}.pdf">Agenda</a></p>' for n in "abcd")
    site = Site({PAGE: httpx.Response(200, content=page(rows))})
    for n in "abcd":
        site.routes[f"https://www.example.gov/f/agenda-{n}.pdf"] = httpx.Response(
            200, content=AGENDA, headers=PDF
        )
    sink = MemorySink()
    run(site, sink, tmp_path, pages=(Page(PAGE, "Example city", ("Travis",), ("x",)),))
    assert [u.rsplit("/", 1)[-1] for u in site.page_urls()[1:]] == ["agenda-a.pdf", "agenda-b.pdf"]
    file = next(d for d in sink.documents.values() if d.url.endswith("agenda-a.pdf"))
    assert file.raw_meta["meeting_date"] is None and file.raw_meta["date_from"] is None


def test_a_page_that_lists_nothing_is_named_in_the_run_log_and_the_run_goes_on(tmp_path):
    site, sink = web(), MemorySink()
    site.routes[COUNTY] = httpx.Response(200, content=page("<p>Moved to a new system.</p>"))
    summary = run(site, sink, tmp_path)
    assert summary.status == "ok"
    assert sink.runs[1]["detail"]["pages_with_no_agenda_links"] == [COUNTY]
    assert site.page_urls() == [COUNTY, MERKEL, *MERKEL_FILES]


def test_a_site_that_refuses_is_left_alone_and_the_other_site_is_read(tmp_path):
    site, sink = web(), MemorySink()
    site.routes[COUNTY_FILES[0]] = httpx.Response(403)
    summary = run(site, sink, tmp_path)
    assert summary.status == "partial"
    # Nothing more was asked of the county's site after it refused.
    assert site.page_urls() == [COUNTY, MERKEL, COUNTY_FILES[0], *MERKEL_FILES]
    assert list(sink.runs[1]["detail"]["refused_hosts"]) == ["www.austincounty.com"]
    assert {d.url for d in sink.documents.values()} == {COUNTY, MERKEL, *MERKEL_FILES}


def test_a_file_host_whose_robots_file_bars_the_collector_is_not_asked(tmp_path):
    inner = '<p><a href="https://img1.wsimg.com/blobby/go/x/11.17.26%20AGENDA.pdf">Agenda</a></p>'
    site = Site({PAGE: httpx.Response(200, content=page(inner))})
    site.routes["https://img1.wsimg.com/robots.txt"] = httpx.Response(
        200, text="User-agent: *\nDisallow: /"
    )
    sink = MemorySink()
    summary = run(site, sink, tmp_path, pages=(Page(PAGE, "Example city", ("Travis",), ("x",)),))
    assert summary.status == "partial"
    assert site.page_urls() == [PAGE]
    assert list(sink.runs[1]["detail"]["refused_hosts"]) == ["img1.wsimg.com"]


def test_an_agenda_on_some_other_host_is_listed_and_not_followed(tmp_path):
    elsewhere = "https://files.example.org/agenda-2026-11-17.pdf"
    site = Site(
        {PAGE: httpx.Response(200, content=page(f'<p><a href="{elsewhere}">Agenda</a></p>'))}
    )
    sink = MemorySink()
    summary = run(site, sink, tmp_path, pages=(Page(PAGE, "Example city", ("Travis",), ("x",)),))
    assert summary.status == "ok"
    assert site.page_urls() == [PAGE]
    assert sink.runs[1]["detail"]["agenda_links_on_other_hosts"] == {PAGE: [elsewhere]}
