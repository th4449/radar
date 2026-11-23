"""The list of known projects, as the backtest reads it. Written before the loader.

Every row here is made up. The real list is checked in its own test below.
"""

from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

import pytest

from backtest.projects import COLUMNS, load_known_projects, to_project


def row(**changes: str) -> dict[str, str]:
    base = {
        "key": "hood-example",
        "name": "Example campus",
        "county": "Hood",
        "place": "near Example",
        "status": "proposed",
        "crypto": "",
        "companies": "Example Holdings LLC; Example Power",
        "code_names": "Project Example; Example One",
        "lat": "32.4",
        "lon": "-97.8",
        "record_date": "2025-03-04",
        "record_kind": "county_notice",
        "record_url": "https://county.example/notice.pdf",
        "record_read": "first_read",
        "news_date": "2025-05-12",
        "news_outlet": "Example Gazette",
        "news_url": "https://gazette.example/story",
        "news_read": "first_read",
        "confidence": "medium",
        "notes": "A made-up row.",
    }
    return {**base, **changes}


def write(tmp_path: Path, *rows: dict[str, str], columns: tuple[str, ...] = COLUMNS) -> Path:
    path = tmp_path / "projects.csv"
    with path.open("w", newline="", encoding="utf-8") as out:
        out.write("# a comment line, skipped\n")
        writer = csv.DictWriter(out, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_a_row_loads_with_its_dates_and_lists(tmp_path: Path) -> None:
    (project,) = load_known_projects(write(tmp_path, row()))
    assert project.record_date == dt.date(2025, 3, 4)
    assert project.news_date == dt.date(2025, 5, 12)
    assert project.companies == ("Example Holdings LLC", "Example Power")
    assert project.code_names == ("Project Example", "Example One")


def test_the_public_date_is_the_first_news_report_not_the_first_record(tmp_path: Path) -> None:
    # The owner's definition of November 22, 2026. A county's own notice is a signal.
    (project,) = load_known_projects(write(tmp_path, row()))
    assert project.public_date == dt.date(2025, 5, 12)


def test_a_project_with_no_news_report_has_no_public_date(tmp_path: Path) -> None:
    quiet = row(news_date="", news_outlet="", news_url="", news_read="none_found")
    (project,) = load_known_projects(write(tmp_path, quiet))
    assert project.public_date is None


def test_a_government_record_ahead_of_the_news_is_counted_in_days(tmp_path: Path) -> None:
    (project,) = load_known_projects(write(tmp_path, row()))
    assert project.government_record_lead_days == 69


@pytest.mark.parametrize(
    "changes",
    [
        {"record_kind": "petition"},  # not a government record
        {"record_kind": "news"},
        {"news_date": "", "news_outlet": "", "news_url": "", "news_read": "none_found"},
        {"record_date": "", "record_kind": "", "record_url": "", "record_read": "set_aside"},
    ],
)
def test_no_lead_is_claimed_without_a_government_record_and_a_news_date(
    tmp_path: Path, changes: dict[str, str]
) -> None:
    (project,) = load_known_projects(write(tmp_path, row(**changes)))
    assert project.government_record_lead_days is None


def test_the_harness_gets_the_county_code_the_names_and_the_point(tmp_path: Path) -> None:
    (known,) = load_known_projects(write(tmp_path, row()))
    project = to_project(known, entity_ids=frozenset({7}))
    assert project.key == "hood-example"
    assert project.county_fips == "48221"
    assert project.public_date == dt.date(2025, 5, 12)
    assert project.names == frozenset({"Project Example", "Example One"})
    assert project.point == (-97.8, 32.4)  # longitude first, as clustering has it
    assert project.entity_ids == frozenset({7})


def test_a_project_with_no_coordinates_has_no_point(tmp_path: Path) -> None:
    (known,) = load_known_projects(write(tmp_path, row(lat="", lon="")))
    assert to_project(known).point is None


def test_a_county_of_two_words_has_a_hyphen_in_its_keys(tmp_path: Path) -> None:
    there = row(key="tom-green-example", county="Tom Green", lat="31.4", lon="-100.4")
    (project,) = load_known_projects(write(tmp_path, there))
    assert to_project(project).county_fips == "48451"


@pytest.mark.parametrize(
    ("changes", "says"),
    [
        ({"county": "Loving"}, "not one of the 30"),
        ({"key": "hill-example"}, "must start with hood-"),
        ({"key": "hood-Example"}, "key"),
        ({"status": "rumored"}, "status"),
        ({"crypto": "maybe"}, "crypto"),
        ({"record_kind": "hearsay"}, "record_kind"),
        ({"record_read": "skimmed"}, "record_read"),
        ({"confidence": "certain"}, "confidence"),
        ({"record_date": "March 4, 2025"}, "record_date"),
        ({"record_url": ""}, "record_date with no address"),
        ({"news_url": ""}, "news_date with no address"),
        ({"record_kind": ""}, "no record_kind"),
        ({"news_read": "none_found"}, "none_found"),
        ({"record_read": "set_aside"}, "set_aside"),
        ({"lon": ""}, "both lat and lon"),
        ({"lat": "45.0"}, "outside Texas"),
        ({"record_url": "county.example/notice.pdf"}, "record_url"),
    ],
)
def test_a_row_that_breaks_a_rule_is_refused(
    tmp_path: Path, changes: dict[str, str], says: str
) -> None:
    with pytest.raises(ValueError, match=says):
        load_known_projects(write(tmp_path, row(**changes)))


def test_two_rows_with_one_key_are_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="twice"):
        load_known_projects(write(tmp_path, row(), row()))


def test_a_file_with_other_columns_is_refused(tmp_path: Path) -> None:
    fewer = COLUMNS[:-1]
    path = write(tmp_path, {k: v for k, v in row().items() if k in fewer}, columns=fewer)
    with pytest.raises(ValueError, match="columns"):
        load_known_projects(path)


def test_the_real_list_loads_and_every_project_is_in_a_test_county() -> None:
    from backtest.projects import KNOWN_PROJECTS_TX

    projects = load_known_projects(KNOWN_PROJECTS_TX)
    assert len(projects) == 128
    assert len({p.county for p in projects}) == 25
    # A page read against a block is never the source of a date.
    assert not [p.key for p in projects if p.record_read == "set_aside" and p.record_date]
    assert not [p.key for p in projects if p.news_read == "set_aside" and p.news_date]


def test_no_read_in_the_real_list_rests_on_a_site_its_robots_file_closes() -> None:
    # known_projects_hosts.csv holds the robots result for every site a read rests on.
    import csv
    from urllib.parse import urlsplit

    from backtest.projects import KNOWN_PROJECTS_TX

    path = KNOWN_PROJECTS_TX.with_name("known_projects_hosts.csv")
    with path.open(encoding="utf-8", newline="") as lines:
        hosts = {
            row["host"]: row["result"]
            for row in csv.DictReader(line for line in lines if not line.startswith("#"))
        }
    assert set(hosts.values()) == {"open", "closed"}
    for project in load_known_projects():
        for url, read in (
            (project.news_url, project.news_read),
            (project.record_url, project.record_read),
        ):
            if read in ("first_read", "second_read"):
                host = urlsplit(url).netloc.lower()
                assert hosts.get(host) == "open", (project.key, host)


def test_the_real_list_keeps_one_row_for_one_site() -> None:
    projects = load_known_projects()
    points = [(p.county, p.lat, p.lon) for p in projects if p.lat is not None]
    assert len(points) == len(set(points))
