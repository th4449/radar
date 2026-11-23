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


def test_no_michigan_government_is_a_collectors_to_read_until_its_row_is_cleared():
    # The collectors are shared code. They ask the inventory of the state they are given, and
    # Michigan's has no confirmed row with its site's terms read.
    from collectors.tx.agenda_pages import cleared_pages
    from collectors.tx.legistar import cleared_clients

    today = dt.date(2026, 11, 23)
    assert cleared_clients(today, state="MI") == []
    assert cleared_pages(today, state="MI") == []
    assert len(cleared_clients(dt.date(2026, 11, 21))) == 9  # Texas is as it was


def test_washtenaw_has_every_government_and_one_governing_body_for_each():
    bodies = [b for b in inv.load_inventory(state="MI") if "Washtenaw" in b.counties]
    places = [name for name, counties in inv.load_places(state="MI") if "Washtenaw" in counties]
    assert len(places) == 28
    governing = collections.Counter(b.government for b in bodies if b.body_type in inv.GOVERNING)
    assert governing == dict.fromkeys(["Washtenaw County", *places], 1)
    # Research only. No row is a collector's until an independent check confirms it.
    assert ac.load_checks(state="MI") == []
