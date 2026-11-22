"""Agenda files that governments post on their own sites.

The page fixtures are real pages, saved on November 21 and 22, 2026 and cut down to the part
that lists agendas. The calendar feeds are real and whole. Each fixture's .meta.json says so.
The agenda files in these tests are made up: a real agenda names people.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import httpx
import pytest

from collectors.base import Fetcher, LayoutChanged, LocalArchive
from collectors.tx.agenda_pages import (
    AgendaLink,
    AgendaPages,
    Page,
    cleared_pages,
    dates_in,
    find_agenda_links,
    find_calendar_feed,
    find_date,
    find_feed_links,
    find_month,
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


def feed(name: str) -> tuple[bytes, str]:
    meta = json.loads((FIXTURES / f"{name}.meta.json").read_text())
    return (FIXTURES / f"{name}.rss").read_bytes(), meta["final_url"]


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
        ("Nov16_2026_Agenda_Regular_Posted", "2026-11-16"),
        ("Dec4_2025_SpecialAgendaPosted.pdf", "2025-12-04"),
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
        "june2026agenda.pdf",  # June 2026, not June 20, 2026
        "Oct2026.pdf",
        "sept_2026_agenda.pdf",
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


@pytest.mark.parametrize(
    ("written", "month"),
    [
        ("November 2026 Agenda", "2026-11"),
        ("November, 2026", "2026-11"),
        ("sept_2026_agenda.pdf", "2026-09"),
        ("june2026agenda.pdf", "2026-06"),
        ("2026-November.docx", "2026-11"),
        ("JULY", None),
        ("city_council_july_16.pdf", None),
        ("March 2031 Agenda", None),  # far from today
        ("Agenda-City-of-DeCordova-11-26.pdf", None),  # November 2026 or November 26
    ],
)
def test_a_month_with_no_day_is_read_as_a_month(written, month):
    assert find_month(written, TODAY) == month


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


def test_a_list_typed_as_one_paragraph_dates_each_link_by_its_own_line():
    found = links("industry")
    # Every link says only "Agenda", and the paragraph holds ten dates. Each line has one.
    assert len(found) == 10
    assert {(link.text, link.date_from) for link in found} == {("Agenda", "line")}
    assert [str(link.date) for link in found][-3:] == ["2026-08-12", "2026-08-26", "2026-09-09"]
    assert found[-1].url.endswith("/september_9.docx")


def test_minutes_and_treasurers_reports_are_left_and_a_month_is_not_made_a_day():
    found = links("decordova")
    # Three lists side by side, each a link to a month. Only the agendas are taken.
    assert len(found) == 10
    assert all("/Agenda-City-of-DeCordova-" in link.url for link in found)
    assert all(link.date is None and link.date_from is None for link in found)
    assert [link.month for link in found][:3] == ["2026-11", "2026-10", "2026-09"]


def test_a_year_in_a_files_name_is_not_read_as_a_day_and_a_year():
    found = {link.url.rsplit("/", 1)[-1]: link for link in links("tolar")}
    # june2026agenda.pdf is June 2026. It was once read as June 20, 2026.
    assert (found["june2026agenda.pdf"].date, found["june2026agenda.pdf"].month) == (
        None,
        "2026-06",
    )
    assert found["sept_2026_agenda.pdf"].month == "2026-09"
    assert str(found["agenda_1-29-26.pdf"].date) == "2026-01-29"
    assert (found["june_s_agenda.pdf"].date, found["june_s_agenda.pdf"].month) == (None, None)


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
    # The county association keeps its counties' calendar files on a host of its own.
    assert on_the_site(
        "https://newtools.cira.state.tx.us/upload/template/1/a.pdf", "https://www.co.hill.tx.us/"
    )
    assert not on_the_site("https://files.example.org/a.pdf", "https://www.example.gov/agendas")
    assert not on_the_site("https://docs.example.gov/a.pdf", "https://www.example.gov/agendas")


# --- a calendar and its feed ----------------------------------------------------------------------

HILL_FEED_BODY, HILL_FEED = feed("hill-county-feed")
HILL_FILE = (
    "https://newtools.cira.state.tx.us/upload/template/28749/docs/CC%202026/"
    "RevisedCCAgendaBriefs11242026.pdf"
)


def rss(*items: str) -> bytes:
    inner = "".join(f"<item>{item}</item>" for item in items)
    return f'<?xml version="1.0"?><rss version="2.0"><channel>{inner}</channel></rss>'.encode()


def test_a_county_association_page_that_lists_its_agendas_by_date():
    found = links("falls-county")
    assert len(found) == 8
    assert found[0] == AgendaLink(
        "https://www.co.falls.tx.us/upload/page/0070/CC%2011%2023%202026.pdf",
        "11/23/2026",
        dt.date(2026, 11, 23),
        "link_text",
    )
    # The page's own date is read, not the one a file's name could be taken for.
    assert [str(link.date) for link in found[2:4]] == ["2026-10-26", "2026-10-12"]
    assert all(link.date_from == "link_text" and " " not in link.url for link in found)


def test_a_calendar_page_lists_no_agenda_itself_and_names_its_feed():
    body, url = saved("hill-county")
    assert find_agenda_links(body, url, TODAY) == []
    assert find_calendar_feed(body) == HILL_FEED
    assert find_calendar_feed(saved("falls-county")[0]) is None


def test_a_calendar_feed_gives_each_meetings_agenda_and_its_day():
    # Hill County: one meeting to come, with its agenda and a link to a video meeting room.
    assert find_feed_links(HILL_FEED_BODY, HILL_FEED) == [
        AgendaLink(HILL_FILE, "Commissioners Court Agenda", dt.date(2026, 11, 24), "calendar_feed")
    ]
    # Carson County: four entries to come. One has an agenda. The others have none yet or are
    # not meetings.
    (carson,) = find_feed_links(*feed("carson-county-feed"))
    assert carson.url == (
        "https://newtools.cira.state.tx.us/upload/template/35997/Agenda%20November%2023%202026.pdf"
    )
    assert (carson.date, carson.date_from) == (dt.date(2026, 11, 23), "calendar_feed")
    # Freestone County had no meeting to come on the day its feed was saved.
    assert find_feed_links(*feed("freestone-county-feed")) == []


def test_an_evening_meeting_is_dated_by_the_day_in_texas():
    """The feed gives Greenwich time. Six in the evening in Texas is the next day there."""
    item = (
        "<title>Commissioners Court</title><pubDate>Tue, 24 Nov 2026 00:00:00 GMT</pubDate>"
        '<description>&lt;a href="/upload/template/1/Agenda.pdf"&gt;Agenda&lt;/a&gt;</description>'
    )
    (link,) = find_feed_links(rss(item), HILL_FEED)
    assert link.date == dt.date(2026, 11, 23)
    # A time that cannot be read dates nothing. The file's own head is read for a date later.
    undated = item.replace("Tue, 24 Nov 2026 00:00:00 GMT", "next Tuesday")
    (link,) = find_feed_links(rss(undated), HILL_FEED)
    assert (link.date, link.date_from) == (None, None)


def test_only_a_file_that_says_it_is_an_agenda_is_taken_from_a_feed():
    def item(*links: tuple[str, str]) -> str:
        said = "".join(f'&lt;a href="{href}"&gt;{text}&lt;/a&gt;' for href, text in links)
        when = "<pubDate>Tue, 24 Nov 2026 15:00:00 GMT</pubDate>"
        return f"<title>Commissioners Court</title>{when}<description>{said}</description>"

    body = rss(
        item(("/upload/a/Minutes 11 10 2026.pdf", "Minutes"), ("/upload/a/Notice.pdf", "Notice")),
        item(("https://meeting.example/1", "Agenda and video link")),
        item(("/upload/a/Agenda Packet.pdf", "Agenda Packet"), ("/upload/a/Agenda.pdf", "Agenda")),
        item(("/upload/a/Agenda.pdf", "Agenda, again")),
    )
    found = find_feed_links(body, HILL_FEED)
    assert [link.url for link in found] == ["https://newtools.cira.state.tx.us/upload/a/Agenda.pdf"]


def test_a_feed_that_is_no_longer_a_feed_is_a_changed_layout():
    for body in (b"<html><body>Not found</body></html>", b"not xml at all", rss()[:-20]):
        with pytest.raises(LayoutChanged):
            find_feed_links(body, HILL_FEED)
    assert find_feed_links(rss(), HILL_FEED) == []  # a feed with no meeting to come is a feed


# --- which pages ----------------------------------------------------------------------------------


def test_the_pages_read_are_the_ones_the_inventory_clears():
    pages = cleared_pages(TODAY)
    governments = {p.government for p in pages}
    assert (len(pages), len(governments)) == (58, 57)
    assert "Austin County" in governments and "Houston city" in governments
    assert "Milam County" in governments
    # The five counties on the sites their association provides.
    assert {
        "Archer County",
        "Carson County",
        "Falls County",
        "Freestone County",
        "Hill County",
    } <= (governments)
    # Closed by a robots file, by its own terms, held for the owner, refused on request, and
    # closed by the robots file of the host that serves its files.
    closed = ("Irving city", "Frankston town", "Austin city", "New Fairview city", "Sealy city")
    assert not governments & set(closed)
    # A site built and hosted by a vendor whose terms bar a collector.
    assert not governments & {
        "Buffalo Gap town",
        "Clyde city",
        "Malakoff city",
        "Mustang Ridge city",
    }
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


def test_links_that_name_only_a_month_give_this_months_and_last_months_files(tmp_path):
    names = ("November 2026", "October 2026", "September 2026", "November 2025")
    rows = "".join(f'<p><a href="/f/{n[:3]}-{n[-4:]}.pdf">{n} Agenda</a></p>' for n in names)
    # One old link has a day. Before, that alone kept every month-only link from being read.
    rows += '<p><a href="/f/old.pdf">Agenda January 5, 2026</a></p>'
    site = Site({PAGE: httpx.Response(200, content=page(rows))})
    for n in names:
        site.routes[f"https://www.example.gov/f/{n[:3]}-{n[-4:]}.pdf"] = httpx.Response(
            200, content=AGENDA, headers=PDF
        )
    sink = MemorySink()
    run(site, sink, tmp_path, pages=(Page(PAGE, "Example city", ("Travis",), ("x",)),))
    assert [u.rsplit("/", 1)[-1] for u in site.page_urls()[1:]] == ["Nov-2026.pdf", "Oct-2026.pdf"]
    file = next(d for d in sink.documents.values() if d.url.endswith("Nov-2026.pdf"))
    assert file.raw_meta["meeting_date"] is None
    assert file.raw_meta["meeting_month"] == "2026-11"


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


# --- a run that reads a calendar feed ------------------------------------------------------------

HILL_BODY, HILL = saved("hill-county")
HILL_PAGE = (Page(HILL, "Hill County", ("Hill",), ("Hill County Commissioners Court",)),)


def calendar_web(feed_body: bytes = HILL_FEED_BODY) -> Site:
    html = {"Content-Type": "text/html; charset=utf-8"}
    return Site(
        {
            HILL: httpx.Response(200, content=HILL_BODY, headers=html),
            HILL_FEED: httpx.Response(
                200, content=feed_body, headers={"Content-Type": "application/rss+xml"}
            ),
            HILL_FILE: httpx.Response(200, content=AGENDA, headers=PDF),
        }
    )


def test_a_calendar_page_has_its_feed_read_and_the_agenda_in_it_fetched(tmp_path):
    site, sink = calendar_web(), MemorySink()
    summary = run(site, sink, tmp_path, pages=HILL_PAGE)
    assert summary.status == "ok", summary.error
    assert site.page_urls() == [HILL, HILL_FEED, HILL_FILE]
    # The page lists nothing itself. Its feed does, so nothing is flagged for a person.
    assert sink.runs[1]["detail"] == {"governments": 1}

    docs = {d.url: d for d in sink.documents.values()}
    assert set(docs) == {HILL, HILL_FEED, HILL_FILE}
    listing = json.loads(LocalArchive(tmp_path).get(docs[HILL_FEED].storage_path))
    assert (listing["government"], listing["page"]) == ("Hill County", HILL)
    assert listing["calendar_feed"] == HILL_FEED
    assert listing["agendas"] == [
        {
            "url": HILL_FILE,
            "text": "Commissioners Court Agenda",
            "date": "2026-11-24",
            "date_from": "calendar_feed",
        }
    ]
    assert docs[HILL_FEED].raw_meta["record"] == "agenda_page"
    # The file is stored with the county's own page, which is what a reviewer opens.
    facts = docs[HILL_FILE].raw_meta
    assert (facts["record"], facts["government"], facts["page"]) == (
        "agenda_file",
        "Hill County",
        HILL,
    )
    assert (facts["meeting_date"], facts["date_from"]) == ("2026-11-24", "calendar_feed")
    assert facts["bodies"] == ["Hill County Commissioners Court"]


def test_a_second_run_asks_for_the_page_and_its_feed_and_not_for_the_stored_file(tmp_path):
    sink = MemorySink()
    run(calendar_web(), sink, tmp_path, pages=HILL_PAGE)
    site = calendar_web()
    summary = run(site, sink, tmp_path, pages=HILL_PAGE)
    assert site.page_urls() == [HILL, HILL_FEED]
    assert (summary.status, summary.documents_new) == ("ok", 0)


def test_a_feed_with_no_agenda_to_come_is_named_in_the_run_log(tmp_path):
    empty, _ = feed("freestone-county-feed")
    site, sink = calendar_web(empty), MemorySink()
    summary = run(site, sink, tmp_path, pages=HILL_PAGE)
    assert summary.status == "ok"
    assert site.page_urls() == [HILL, HILL_FEED]
    assert sink.runs[1]["detail"]["pages_with_no_agenda_links"] == [HILL]


def test_a_feed_that_changed_stops_the_run_for_a_person_to_look(tmp_path):
    site, sink = calendar_web(b"<html><body>Moved</body></html>"), MemorySink()
    summary = run(site, sink, tmp_path, pages=HILL_PAGE)
    assert summary.status == "failed" and "calendar feed" in summary.error
    assert site.page_urls() == [HILL, HILL_FEED]
