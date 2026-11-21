"""A row of the agenda inventory is trusted only when an independent check agrees with it."""

from __future__ import annotations

import datetime as dt

import pytest
from pydantic import ValidationError

from pipeline import agenda_checks as ac
from pipeline import agenda_inventory as inv

TODAY = dt.date(2026, 11, 21)
COUNCIL = "Example City Council"
PLANNING = "Example Planning and Zoning Commission"
PAGE = "https://www.example-tx.gov/AgendaCenter"
FILE = "https://www.example-tx.gov/AgendaCenter/ViewFile/Agenda/_11172026-101"


def body(**changes) -> inv.AgendaBody:
    base = {
        "government": "Example city",
        "counties": ("Hood",),
        "body": COUNCIL,
        "body_type": "city_council",
        "official_site": "https://www.example-tx.gov/",
        "agenda_url": PAGE,
        "platform": "civicplus_agendacenter",
        "evidence": FILE,
        "status": "seen",
        "notes": "",
    }
    return inv.AgendaBody(**{**base, **changes})


def check(**changes) -> ac.Check:
    base = {
        "government": "Example city",
        "kind": "read_page",
        "page": PAGE,
        "checked_on": TODAY,
        "by": "second_read",
        "result": "read",
        "opened": PAGE,
        "followed_to": "",
        "names_texas": "yes",
        "agenda_links": (FILE,),
        "agendas_listed": 12,
        "newest_agenda_date": dt.date(2026, 11, 17),
        "bodies_listed": (COUNCIL,),
        "other_hosts": (),
        "notes": "",
    }
    return ac.Check(**{**base, **changes})


def platforms(**status: str) -> dict[str, inv.PlatformTerms]:
    """Every platform cleared, except the ones given another status."""
    return {
        name: inv.PlatformTerms(
            platform=name,
            vendor="Example vendor",
            status=status.get(name, "cleared"),
            robots="allowed",
            checked_on="" if status.get(name) == "not_read" else "2026-11-21",
            terms_url="",
            note="Made up for a test.",
        )
        for name in inv.FOUND
    }


def earned(row: inv.AgendaBody, *checks: ac.Check, today: dt.date = TODAY) -> str:
    return ac.verdict(row, ac.Checks(list(checks)), today)[0]


# --- the only way to be confirmed ---------------------------------------------------------------


def test_a_row_is_confirmed_when_a_check_saw_the_same_platform_body_and_a_recent_agenda():
    assert earned(body(), check()) == "confirmed"
    assert ac.collectable(body(), ac.Checks([check()]), TODAY, platforms())


def test_a_confirmed_row_is_still_not_collected_from_a_platform_that_is_not_cleared():
    """Being right about where the agendas are is not permission to collect them."""
    confirmed = ac.Checks([check()])
    for status in ("restricted", "candidate", "not_read"):
        barred = platforms(civicplus_agendacenter=status)
        assert not ac.collectable(body(), confirmed, TODAY, barred), status
    assert not ac.collectable(body(), confirmed, TODAY, {})


def test_a_row_nobody_checked_is_not_trusted():
    assert earned(body()) == "unchecked"
    assert not ac.collectable(body(), ac.Checks([]), TODAY, platforms())
    # A check of another page of the same government does not count.
    other = check(page="https://www.example-tx.gov/meetings")
    assert earned(body(), other) == "unchecked"


def test_a_trailing_slash_or_capital_letter_is_the_same_page():
    assert earned(body(), check(page=PAGE.upper().replace("HTTPS", "https") + "/")) == "confirmed"


# --- disagreement -------------------------------------------------------------------------------


def test_another_platform_on_the_page_contradicts_the_row():
    legistar = "https://example.legistar.com/View.ashx?M=A&ID=1"
    got, why = ac.verdict(body(), ac.Checks([check(agenda_links=(legistar,))]), TODAY)
    assert got == "contradicted" and "legistar" in why


def test_an_empty_platform_page_confirms_nothing():
    """The fault found by hand in Southside Place: an Agenda Center page with nothing on it."""
    empty = check(agenda_links=(), agendas_listed=0, newest_agenda_date=None, bodies_listed=())
    assert earned(body(), empty) == "not_shown"


def test_own_site_files_where_the_row_names_a_platform_contradicts_it():
    files = ("https://www.example-tx.gov/files/agenda-2026-11-17.pdf",)
    assert earned(body(), check(agenda_links=files, opened="https://www.example-tx.gov/x")) == (
        "contradicted"
    )


def test_a_platform_where_the_row_says_own_site_contradicts_it():
    row = body(
        agenda_url="https://www.example-tx.gov/agendas",
        platform="own_site_files",
        evidence="https://www.example-tx.gov/files/a.pdf",
    )
    page = "https://www.example-tx.gov/agendas"
    agree = check(page=page, opened=page, agenda_links=("https://www.example-tx.gov/files/b.pdf",))
    assert earned(row, agree) == "confirmed"
    clerk = check(page=page, opened=page, agenda_links=("https://ex.portal.civicclerk.com/e/1",))
    assert earned(row, clerk) == "contradicted"
    # A video host named beside the agendas is not a contradiction.
    video = check(
        page=page,
        opened=page,
        agenda_links=("https://www.example-tx.gov/files/b.pdf",),
        other_hosts=("exampletx.new.swagit.com",),
    )
    assert earned(row, video) == "confirmed"


def test_a_page_for_another_state_contradicts_the_row():
    assert earned(body(), check(names_texas="no")) == "contradicted"


def test_a_platform_reached_through_a_link_from_the_citys_page_agrees():
    row = body(
        agenda_url="https://www.example-tx.gov/meetings",
        platform="civicclerk",
        evidence="https://exampletx.portal.civicclerk.com/",
    )
    page = "https://www.example-tx.gov/meetings"
    seen = check(
        page=page,
        opened=page,
        agenda_links=(),
        agendas_listed=0,
        other_hosts=("exampletx.portal.civicclerk.com",),
    )
    # The platform is linked, but no agenda was seen: not confirmed.
    assert earned(row, seen) == "not_shown"
    full = check(
        page=page,
        opened=page,
        followed_to="https://exampletx.portal.civicclerk.com/",
        agenda_links=("https://exampletx.portal.civicclerk.com/event/9/files",),
    )
    assert earned(row, full) == "confirmed"


def test_agendas_that_open_by_script_count_when_they_are_listed_on_the_right_site():
    """A real browser sees a dated list whose entries open by script and give no address."""
    row = body(
        agenda_url="https://www.example-tx.gov/agendas",
        platform="own_site_files",
        evidence="https://www.example-tx.gov/files/a.pdf",
    )
    page = "https://www.example-tx.gov/agendas"
    listed = check(page=page, opened=page, agenda_links=(), agendas_listed=34, by="browser_read")
    assert earned(row, listed) == "confirmed"
    # For an outside platform the list must be on that platform's own address.
    portal = "https://exampletx.portal.civicclerk.com/"
    clerk = body(agenda_url=portal, platform="civicclerk", evidence=portal)
    on_portal = check(page=portal, opened=portal, agenda_links=(), agendas_listed=20)
    assert earned(clerk, on_portal) == "confirmed"
    on_city_page = check(
        page=PAGE, opened="https://www.example-tx.gov/x", agenda_links=(), agendas_listed=20
    )
    legistar = body(platform="legistar", evidence="https://example.legistar.com/Calendar.aspx")
    assert earned(legistar, on_city_page) == "contradicted"
    with pytest.raises(ValidationError, match="fewer agendas listed"):
        check(agendas_listed=0)


# --- agreement that is not enough ---------------------------------------------------------------


def test_a_body_not_seen_on_the_page_is_not_confirmed_by_its_governments_platform():
    planning = body(body=PLANNING, body_type="planning_body", status="inferred")
    assert earned(planning, check()) == "government_only"
    assert earned(planning, check(bodies_listed=(COUNCIL, PLANNING))) == "confirmed"


def test_an_old_or_undated_list_is_not_current():
    old = check(newest_agenda_date=dt.date(2023, 4, 11))
    got, why = ac.verdict(body(), ac.Checks([old]), TODAY)
    assert got == "not_current" and "2023-04-11" in why
    assert earned(body(), check(newest_agenda_date=None)) == "not_current"


def test_a_page_with_no_agenda_addresses_is_not_shown():
    assert (
        earned(body(), check(agenda_links=(), agendas_listed=0, newest_agenda_date=None))
        == "not_shown"
    )


@pytest.mark.parametrize("result", ["empty", "blocked", "error"])
def test_a_page_the_check_could_not_read_is_unreadable(result):
    blank = check(
        result=result, agenda_links=(), agendas_listed=0, newest_agenda_date=None, bodies_listed=()
    )
    assert earned(body(), blank) == "unreadable"


def test_a_check_goes_stale():
    assert earned(body(), check(), today=TODAY + dt.timedelta(days=ac.RECHECK_DAYS)) == "confirmed"
    assert earned(body(), check(), today=TODAY + dt.timedelta(days=ac.RECHECK_DAYS + 1)) == (
        "expired"
    )


# --- nothing found ------------------------------------------------------------------------------

NOSITE = {
    "official_site": "",
    "agenda_url": "",
    "platform": "no_website",
    "evidence": "",
    "status": "not_found",
    "notes": "Facebook page only",
}
SEARCH = {
    "kind": "find_site",
    "page": "",
    "agenda_links": (),
    "agendas_listed": 0,
    "newest_agenda_date": None,
}


def test_no_website_holds_only_when_a_second_search_also_found_none():
    row = body(**NOSITE)
    assert earned(row) == "unchecked"
    none = check(**SEARCH, result="not_found", opened="", bodies_listed=(), names_texas="unknown")
    assert earned(row, none) == "agreed_none"
    found = check(**SEARCH, opened="https://www.example-tx.gov/", bodies_listed=())
    assert earned(row, found) == "contradicted"
    # A same-named town in another state is not a find.
    elsewhere = check(**SEARCH, opened="https://www.example-il.gov/", names_texas="no")
    assert earned(row, elsewhere) == "agreed_none"


def test_a_row_with_no_agenda_page_is_undetermined_until_a_read_finds_one():
    row = body(
        agenda_url="", platform="not_determined", evidence="", status="not_found", notes="Blocked."
    )
    assert earned(row) == "undetermined"
    found = check(kind="find_agendas", page="", opened="https://www.example-tx.gov/agendas")
    assert earned(row, found) == "contradicted"
    corporation = body(
        body="Example Economic Development Corporation",
        body_type="development_corporation",
        agenda_url="",
        platform="not_determined",
        evidence="",
        status="not_found",
        notes="Not looked up.",
    )
    assert earned(corporation, found) == "undetermined"


# --- which check decides ------------------------------------------------------------------------


def test_the_newest_check_decides_and_a_hand_check_outranks_a_second_read():
    earlier = check(
        checked_on=TODAY - dt.timedelta(days=10),
        agenda_links=(),
        agendas_listed=0,
        bodies_listed=(),
    )
    assert earned(body(), earlier, check()) == "confirmed"
    assert earned(body(), check(), earlier) == "confirmed"
    by_hand = check(by="hand", names_texas="no")
    assert earned(body(), check(), by_hand) == "contradicted"
    assert earned(body(), by_hand, check()) == "contradicted"
    in_browser = check(by="browser_read")
    blank = check(
        result="empty", agenda_links=(), agendas_listed=0, newest_agenda_date=None, bodies_listed=()
    )
    assert earned(body(), blank, in_browser) == "confirmed"
    assert earned(body(), in_browser, blank) == "confirmed"
    assert earned(body(), in_browser, by_hand) == "contradicted"


# --- what a check may hold ----------------------------------------------------------------------


def test_a_check_holds_addresses_and_dates_and_nothing_personal():
    with pytest.raises(ValidationError, match="not a web address"):
        check(agenda_links=("Agenda for November",))
    with pytest.raises(ValidationError, match="no email address"):
        check(notes="write to clerk@example-tx.gov")
    with pytest.raises(ValidationError, match="far in the future"):
        check(newest_agenda_date=dt.date(2027, 11, 17))
    with pytest.raises(ValidationError, match="no address opened"):
        check(opened="")
    with pytest.raises(ValidationError, match="carries a key or token"):
        check(agenda_links=("https://drive.google.com/drive/folders/abc?resourcekey=0-xyz",))


def test_checks_survive_being_written_and_read(tmp_path):
    path = tmp_path / "checks.csv"
    checks = [
        check(),
        check(
            kind="find_site",
            page="",
            result="not_found",
            opened="",
            agenda_links=(),
            agendas_listed=0,
            newest_agenda_date=None,
            bodies_listed=(),
            other_hosts=("a.example.org", "b.example.org"),
            notes="Two searches, a directory only.",
        ),
    ]
    ac.write_checks(checks, path, header="# a comment line\n")
    assert ac.load_checks(path) == checks


# --- the files ----------------------------------------------------------------------------------


def test_every_check_on_file_is_about_a_government_in_the_inventory():
    governments = {b.government for b in inv.load_inventory()}
    for c in ac.load_checks():
        assert c.government in governments, c.government


def test_the_report_counts_every_row_once():
    bodies = inv.load_inventory()
    text = ac.report(bodies, ac.Checks(ac.load_checks()), TODAY, listing=True)
    assert text.startswith(f"{len(bodies)} bodies")
    listed = [line for line in text.splitlines() if " | " in line]
    settled = sum(
        1 for b in bodies if ac.verdict(b, ac.Checks(ac.load_checks()), TODAY)[0] in ac.SETTLED
    )
    assert len(listed) == len(bodies) - settled


def test_the_hand_read_list_has_every_unsettled_row_and_courts_first():
    bodies = inv.load_inventory()
    checks = ac.Checks(ac.load_checks())
    lines = ac.queue_csv(bodies, checks, TODAY).splitlines()
    unsettled = [b for b in bodies if ac.verdict(b, checks, TODAY)[0] not in ac.SETTLED]
    assert len(lines) - 1 == len(unsettled)
    kinds = [line.split(",")[-3] for line in lines[1:] if "commissioners_court" in line]
    assert kinds and all(k == "commissioners_court" for k in kinds)
    first_other = next(i for i, line in enumerate(lines[1:]) if "commissioners_court" not in line)
    assert all("commissioners_court" not in line for line in lines[1 + first_other :])


def test_no_collector_may_take_a_row_that_is_not_confirmed():
    """The gate every agenda collector goes through, with every platform cleared for the test."""
    bodies = inv.load_inventory()
    checks = ac.Checks(ac.load_checks())
    cleared = platforms()
    for b in bodies:
        name, _ = ac.verdict(b, checks, TODAY)
        assert ac.collectable(b, checks, TODAY, cleared) == (name == "confirmed")
        if name == "confirmed":
            assert b.agenda_url and b.platform in inv.FOUND


def test_nothing_is_collectable_today():
    """No platform is cleared, so the gate lets nothing through. This is the state on file."""
    bodies = inv.load_inventory()
    checks = ac.Checks(ac.load_checks())
    assert not [b.body for b in bodies if ac.collectable(b, checks, TODAY)]
