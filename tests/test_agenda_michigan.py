"""The agenda inventory for a second state. BUILD_PLAN.md milestone M11.

Michigan's local governments are counties, cities, villages and townships. A township is not
in the Census list of places: it is a county subdivision with its own board. The six counties
whose agendas come first are Allegan, Kalamazoo, Monroe, Oakland, Washtenaw and Wayne.
"""

from __future__ import annotations

import collections
import datetime as dt

import pytest

from pipeline import agenda_checks as ac
from pipeline import agenda_inventory as inv
from pipeline.config import load_counties

SIX = {"Allegan", "Kalamazoo", "Monroe", "Oakland", "Washtenaw", "Wayne"}


def test_the_six_counties_are_the_ones_the_county_file_marks_first():
    assert inv.agenda_counties("MI") == SIX
    assert inv.agenda_counties("TX") == {c.name for c in load_counties("TX").counties}


def test_the_michigan_place_list_holds_every_city_village_and_township_once():
    places = inv.load_places(state="MI")
    names = [name for name, _ in places]
    assert len(names) == len(set(names)) == 214
    kinds = collections.Counter(
        "township" if "township" in name else name.rsplit(" ", 1)[-1] for name in names
    )
    assert kinds == {"city": 86, "village": 24, "township": 104}
    assert {c for _, counties in places for c in counties} == SIX
    # Two townships share a name. Each carries its county.
    assert "Salem township (Washtenaw County)" in names
    assert "Salem township (Allegan County)" in names
    # A city can lie in two of the six counties.
    assert dict(places)["Milan city"] == ("Monroe", "Washtenaw")
    # The Texas list is as it was.
    assert len(inv.load_places()) == 304


def row(**changes: str) -> dict[str, str]:
    base = {
        "government": "Example township",
        "counties": "Washtenaw",
        "body": "Example Township Board of Trustees",
        "body_type": "township_board",
        "official_site": "https://www.example-twp.org/",
        "agenda_url": "https://www.example-twp.org/agendas",
        "platform": "own_site_files",
        "evidence": "https://www.example-twp.org/files/agenda-2026-11-10.pdf",
        "status": "seen",
        "notes": "Agendas listed by year.",
    }
    return {**base, **changes}


def write(tmp_path, *rows):
    import csv

    path = tmp_path / "inventory.csv"
    with path.open("w", newline="", encoding="utf-8") as out:
        out.write("# a comment line\n")
        writer = csv.DictWriter(out, fieldnames=list(row()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_a_michigan_row_loads_with_its_own_kinds_of_body(tmp_path):
    rows = [
        row(),
        row(government="Washtenaw County", body="Washtenaw County Board of Commissioners",
            body_type="county_board"),
        row(government="Manchester village", body="Manchester Village Council",
            body_type="village_council"),
        row(government="Saline city", body="Saline City Council", body_type="city_council"),
        row(body="Example Township Planning Commission", body_type="planning_body"),
    ]  # fmt: skip
    bodies = inv.load_inventory(write(tmp_path, *rows), state="MI")
    assert [b.body_type for b in bodies] == [
        "township_board", "county_board", "village_council", "city_council", "planning_body",
    ]  # fmt: skip
    assert all(b.body_type in inv.GOVERNING for b in bodies[:4])
    assert bodies[4].body_type not in inv.GOVERNING


def test_a_michigan_row_in_a_county_outside_the_six_is_refused(tmp_path):
    with pytest.raises(ValueError, match="Ingham"):
        inv.load_inventory(write(tmp_path, row(counties="Ingham")), state="MI")
    # And a Michigan county is not a Texas one.
    with pytest.raises(ValueError, match="Washtenaw"):
        inv.load_inventory(write(tmp_path, row()), state="TX")


def test_the_michigan_inventory_file_loads():
    bodies = inv.load_inventory(state="MI")
    for body in bodies:
        assert set(body.counties) <= SIX
    places = dict(inv.load_places(state="MI"))
    for body in bodies:
        if not body.government.endswith(" County"):
            assert body.government in places, body.government
            assert body.counties == places[body.government], body.body


def test_a_check_says_whether_the_page_is_for_a_place_in_the_right_state():
    check = ac.Check(
        government="Example township",
        kind="read_page",
        page="https://www.example-twp.org/agendas",
        checked_on=dt.date(2026, 11, 23),
        by="second_read",
        result="read",
        opened="https://www.example-twp.org/agendas",
        followed_to="",
        names_state="no",
        agenda_links=(),
        agendas_listed=0,
        newest_agenda_date=None,
        bodies_listed=(),
        other_hosts=(),
        notes="The page is for a township of the same name in another state.",
    )
    assert check.names_state == "no"
    assert "names_state" in ac.COLUMNS and "names_texas" not in ac.COLUMNS


def test_each_state_has_its_own_checks_and_site_terms_files():
    assert ac.load_checks(state="MI") == [] or all(c.government for c in ac.load_checks(state="MI"))
    assert len(ac.load_checks()) > 300  # the Texas file, by default
    assert inv.load_site_terms(state="MI") == [] or inv.load_site_terms(state="MI")[0]["host"]
    assert len(inv.load_site_terms()) > 100


HELD = (
    "access_means_clause",
    "noncommercial_only",  # no Michigan row carries it now. Texas has none either
    "reuse_needs_consent",
    "vendor_site",
    "could_not_read",
    "robots_bar",
    "refused",
)


def test_a_michigan_row_is_cleared_only_when_confirmed_and_every_host_of_its_site_allows_it():
    today = dt.date(2026, 11, 23)
    bodies = inv.load_inventory(state="MI")
    checks = ac.Checks(ac.load_checks(state="MI"))
    sites = inv.load_site_terms(state="MI")
    platforms = inv.load_platform_terms()
    results = collections.defaultdict(set)
    for row in sites:
        results[(row["government"], row["platform"])].add(row["result"])
    assert {r for rs in results.values() for r in rs} <= {*ac.SITE_ALLOWS, *HELD}
    cleared = [b for b in bodies if ac.collectable(b, checks, today, platforms, sites, state="MI")]
    assert cleared
    for b in cleared:
        assert ac.verdict(b, checks, today)[0] == "confirmed"
        assert b.platform in ("own_site_files", "legistar")
        assert results[(b.government, b.platform)] <= set(ac.SITE_ALLOWS)
    governments = {b.government for b in cleared}
    # Sites whose terms are held for the owner, or built by a vendor whose terms bar a collector.
    for held in (
        "Rochester city",
        "Ross township",
        "Rockwood city",
        "Detroit city",
    ):
        assert held not in governments
    # Texas is as it was.
    from collectors.tx.legistar import cleared_clients

    assert len(cleared_clients(dt.date(2026, 11, 21))) == 9


def test_three_sites_whose_terms_allow_non_commercial_use_are_cleared_on_the_owners_word():
    """The owner said on November 25, 2026 to read the sites that allow non-commercial use."""
    today = dt.date(2026, 11, 25)
    assert "noncommercial_cleared" in ac.SITE_ALLOWS
    assert "noncommercial_only" not in ac.SITE_ALLOWS
    sites = inv.load_site_terms(state="MI")
    cleared = {r["government"]: r for r in sites if r["result"] == "noncommercial_cleared"}
    assert set(cleared) == {"Keego Harbor city", "Southgate city", "Dearborn city"}
    for row in cleared.values():
        # The sentence that was read stays in the note, with the day the owner cleared it.
        assert "non-commercial" in row["note"] or "Commercial use" in row["note"]
        assert "The owner cleared it on 2026-11-25" in row["note"]
    # None is left held under the old mark, and the other five held sites are as they were.
    assert not [r for r in sites if r["result"] == "noncommercial_only"]
    still = {
        r["government"]
        for r in sites
        if r["result"] in ("access_means_clause", "reuse_needs_consent")
    }
    assert still == {
        "Otsego township",
        "Berlin charter township",
        "Plymouth charter township",
        "Ross township",
        "Rockwood city",
    }
    bodies = inv.load_inventory(state="MI")
    checks = ac.Checks(ac.load_checks(state="MI"))
    takes = {b.government for b in bodies if ac.collectable(b, checks, today, state="MI")}
    assert set(cleared) <= takes
    assert not still & takes
    # Texas' four sites with like terms are not cleared by this.
    texas = inv.load_site_terms()
    assert not [r for r in texas if r["result"] == "noncommercial_cleared"]


def test_no_job_reads_a_michigan_agenda_source_yet():
    # A cleared row is a row a collector could take. Whether any collector runs is the source's
    # setting, and both Michigan agenda sources are still collected by nobody.
    from pipeline import config

    sources = {s.id: s for s in config.load_sources().sources}
    for name in ("mi_agendas_legistar", "mi_agendas_own_sites"):
        assert sources[name].method == "manual"


def test_washtenaw_has_every_government_and_one_governing_body_for_each():
    bodies = [b for b in inv.load_inventory(state="MI") if "Washtenaw" in b.counties]
    places = [name for name, counties in inv.load_places(state="MI") if "Washtenaw" in counties]
    assert len(places) == 28
    governing = collections.Counter(b.government for b in bodies if b.body_type in inv.GOVERNING)
    assert governing == dict.fromkeys(["Washtenaw County", *places], 1)


def test_michigan_checks_are_second_reads_of_pages_the_inventory_names():
    checks = ac.load_checks(state="MI")
    bodies = inv.load_inventory(state="MI")
    pages = {(b.government, b.agenda_url.rstrip("/").lower()) for b in bodies if b.agenda_url}
    assert len(checks) >= 195
    for c in checks:
        assert c.kind == "read_page"
        assert (c.government, c.page.rstrip("/").lower()) in pages, c.page
        # A read sent to a page on the government's own site or on Legistar, and nowhere else.
        assert inv.platform_of(c.page) in (None, "legistar"), c.page
    assert len({(c.government, c.page) for c in checks}) == len(checks)


def test_most_michigan_candidate_rows_are_confirmed_and_every_site_has_a_terms_row():
    checks = ac.Checks(ac.load_checks(state="MI"))
    today = dt.date(2026, 11, 23)
    verdicts = [ac.verdict(b, checks, today)[0] for b in inv.load_inventory(state="MI")]
    assert verdicts.count("confirmed") > 150
    # Each site's own terms were read on November 23, 2026: one row for each host.
    hosts = [row["host"] for row in inv.load_site_terms(state="MI")]
    assert len(hosts) == len(set(hosts)) >= 90


def test_every_government_in_the_six_counties_has_one_governing_body():
    bodies = inv.load_inventory(state="MI")
    places = [name for name, _ in inv.load_places(state="MI")]
    counties = [f"{name} County" for name in sorted(SIX)]
    governing = collections.Counter(b.government for b in bodies if b.body_type in inv.GOVERNING)
    assert governing == dict.fromkeys([*counties, *places], 1)
    assert len(governing) == 220


def test_a_county_board_governs_a_county_and_nothing_else():
    for body in inv.load_inventory(state="MI"):
        if body.body_type == "county_board":
            assert body.government.endswith(" County"), body.body
        if body.government.endswith(" County") and body.body_type in inv.GOVERNING:
            assert body.body_type == "county_board", body.body
        assert body.body_type != "commissioners_court", body.body
