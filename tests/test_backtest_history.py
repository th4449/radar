"""Stored history, read as dated signals for the backtest. Written before the loader.

Every company, project and agenda here is made up. These tests pin three things the report
leans on: the day a record counts from, when a company counts as listed, and when a record is
said to name a known project.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json

from backtest.history import (
    History,
    harness_projects,
    history_rules,
    listed_since,
    read,
)
from backtest.projects import KnownProject
from collectors.tx import twdb_well_reports as twdb
from pipeline.signals import Doc, Listing

WHEN = dt.datetime(2026, 11, 23, 6, 0, tzinfo=dt.UTC)
RULES = history_rules(None)


def known(key: str, county: str, *companies: str, code_names: tuple[str, ...] = (), **more):
    base = {
        "key": key,
        "name": "Made-up campus",
        "county": county,
        "place": "",
        "status": "proposed",
        "crypto": "",
        "companies": companies,
        "code_names": code_names,
        "lat": None,
        "lon": None,
        "record_date": None,
        "record_kind": "",
        "record_url": "",
        "record_read": "none_found",
        "news_date": dt.date(2026, 6, 1),
        "news_outlet": "Example Gazette",
        "news_url": "https://gazette.example/story",
        "news_read": "first_read",
        "confidence": "low",
        "notes": "",
    }
    return KnownProject(**{**base, **more})


def _doc(source: str, url: str, body: bytes, text: str = "", meta: dict | None = None) -> Doc:
    return Doc(source, url, WHEN, hashlib.sha256(body).hexdigest(), text, meta or {}, body)


def legistar(*titles: str, published: str | None = "2026-03-05T16:00:00", **changes) -> Doc:
    agenda = {
        "platform": "legistar",
        "client": "exampletx",
        "government": "Example city",
        "counties": ["Milam"],
        "event_id": 41,
        "date": "2026-03-09",
        "body": "City Council",
        "agenda_published": published,
        "page": "https://exampletx.legistar.com/MeetingDetail.aspx?LEGID=41",
        "items": [
            {"id": str(n), "sequence": n, "number": f"{n}.", "file": "", "type": "",
             "name": "", "title": title, "note": ""}
            for n, title in enumerate(titles, 1)
        ],
        **changes,
    }  # fmt: skip
    body = json.dumps(agenda).encode()
    url = "https://webapi.legistar.com/v1/exampletx/events/41?EventItems=1&AgendaNote=1"
    meta = {
        "record": "legistar_agenda",
        "event_date": agenda["date"],
        "counties": agenda["counties"],
        "government": agenda["government"],
    }
    return _doc("tx_agendas_legistar", url, body, meta=meta)


def agenda_file(*pages: str, url: str = "https://www.example.gov/files/a.pdf", **meta) -> Doc:
    facts = {
        "record": "agenda_file",
        "government": "Milam County",
        "counties": ["Milam"],
        "bodies": ["Milam County Commissioners Court"],
        "page": "https://www.example.gov/agendas",
        "meeting_date": "2026-01-12",
        "date_from": "link_text",
        "last_modified": "Thu, 08 Jan 2026 15:00:00 GMT",
        **meta,
    }
    text = "\n\n".join(("NOTICE OF MEETING AND AGENDA", *pages))
    return _doc("tx_agendas_own_sites", url, b"%PDF" + text.encode(), text, facts)


def wells(*rows: dict[str, str]) -> Doc:
    lines = ["|".join(twdb.KEEP)]
    for number, values in enumerate(rows, 9100001):
        row = dict.fromkeys(twdb.KEEP, "")
        row.update(
            WellReportTrackingNumber=str(number), DateSubmitted="2026-02-03", County="Milam",
            OwnerName="Example Data Center LLC", ProposedUse="Industrial", TypeOfWork="New Well",
            CoordDDLat="30.65", CoordDDLong="-97.00",
        )  # fmt: skip
        row.update(values)
        lines.append("|".join(row[name] for name in twdb.KEEP))
    return _doc("tx_twdb_well_reports", twdb.URL, ("\n".join(lines) + "\n").encode())


def planning_file(text: str, posted: str = "2025/04/28") -> Doc:
    url = f"https://www.ercot.com/files/docs/{posted}/Example_Project_RPG.pdf"
    return _doc("tx_ercot_rpg", url, b"%PDF" + text.encode(), text)


def history(*docs: Doc, projects=(), rules=RULES, since=None) -> History:
    return read(enumerate(docs, 1), rules, projects, since or {})


def one(made: History):
    (record,) = made.records
    return record


# --- which counties are read ---------------------------------------------------------------------


def test_the_rules_read_the_test_counties_and_the_control_counties():
    counties = RULES.counties["TX"]
    assert counties.fips("Hood") == "48221"
    assert counties.fips("Lamb") == "48279"  # a control county
    assert counties.fips("Loving") is None


# --- the day a record counts from ---------------------------------------------------------------


def test_a_legistar_agenda_counts_from_the_day_it_was_published():
    record = one(history(legistar("Discuss a proposed data center on County Road 12")))
    assert record.signal.event_date == dt.date(2026, 3, 9)
    assert record.signal.available_on == dt.date(2026, 3, 5)
    assert "published" in record.seen_basis


def test_an_agenda_published_again_after_its_meeting_counts_from_the_meeting():
    late = legistar("Discuss a proposed data center", published="2026-08-01T09:00:00")
    assert one(history(late)).signal.available_on == dt.date(2026, 3, 9)
    undated = legistar("Discuss a proposed data center", published=None)
    assert one(history(undated)).signal.available_on == dt.date(2026, 3, 9)


def test_an_agenda_file_counts_from_the_day_of_its_meeting():
    # The file's own date is earlier. A file can be put up again, so it is not trusted.
    record = one(history(agenda_file("3. Hear a report on the proposed data center.")))
    assert record.signal.available_on == dt.date(2026, 1, 12)


def test_a_well_report_counts_from_the_day_it_was_submitted():
    record = one(history(wells({})))
    assert record.signal.available_on == dt.date(2026, 2, 3)
    assert record.signal.point == (-97.0, 30.65)
    assert record.signal.entity_id is not None
    assert record.party == "Example Data Center LLC"


def test_a_planning_file_counts_from_the_day_in_its_address():
    record = one(history(planning_file("A new 300 MW large load in Milam County.")))
    assert record.signal.available_on == dt.date(2025, 4, 28)
    assert record.signal.signal_type == "transmission_filing"


def test_the_same_fact_in_a_later_copy_is_one_signal():
    assert len(history(wells({}), wells({})).records) == 1


def test_signals_are_numbered_in_the_order_they_were_read():
    made = history(wells({}, {"DateSubmitted": "2026-02-04"}), legistar("A data center item"))
    assert [r.signal.signal_id for r in made.records] == [1, 2, 3]
    assert made.counts["tx_twdb_well_reports"]["signals"] == 2


# --- a company counts as listed only from the day its registration took effect ------------------

LISTED = {"EXAMPLE HOSTING INC": [Listing("Example Hosting, Inc.", "owner", "EX1", "qualifying")]}
LISTED_RULES = history_rules(None, listings=LISTED)
SINCE = {("qualifying", "EX1"): dt.date(2026, 2, 1)}


def test_a_listed_company_is_a_reason_only_after_its_registration_took_effect():
    before = wells({"OwnerName": "Example Hosting, Inc.", "DateSubmitted": "2026-01-15"})
    after = wells({"OwnerName": "Example Hosting, Inc.", "DateSubmitted": "2026-02-15"})
    early = history(before, rules=LISTED_RULES, since=SINCE)
    assert early.records == [] and early.listed_later == 1
    late = one(history(after, rules=LISTED_RULES, since=SINCE))
    assert late.rule == "listed_company"


def test_a_registration_with_no_readable_date_is_never_a_reason():
    row = wells({"OwnerName": "Example Hosting, Inc."})
    made = history(row, rules=LISTED_RULES, since={("qualifying", "EX1"): None})
    assert made.records == [] and made.listed_later == 1


def test_the_words_still_count_when_the_listing_came_later():
    row = wells(
        {"OwnerName": "Example Hosting, Inc.", "DateSubmitted": "2026-01-15",
         "ProposedUseOtherDesc": "cooling water for a data center"}
    )  # fmt: skip
    record = one(history(row, rules=LISTED_RULES, since=SINCE))
    assert record.rule == "direct_term"
    assert record.signal.confidence == 0.9


def test_the_real_list_gives_each_registration_its_effective_date():
    from pathlib import Path

    page = Path(__file__).parent / "fixtures/tx_comptroller_data_centers/data-center-lists.html"
    since = listed_since(page.read_bytes())
    assert len(since) > 150
    assert any(day is None for day in since.values())  # two dates the state mistyped
    assert all(day is None or day.year >= 2013 for day in since.values())


# --- when a record is said to name a known project ----------------------------------------------

RIVER = known("milam-example-river", "Milam", "Example River LLC", "Example Platforms")
OTHER = known("hill-example-river", "Hill", "Example River LLC")
ABATEMENT = "Tax abatement agreement with Example River, LLC for a data center"


def test_a_record_that_carries_a_projects_company_names_the_project():
    record = one(history(legistar(ABATEMENT), projects=[RIVER, OTHER]))
    assert record.names_projects == ("milam-example-river",)  # never the one in another county
    assert record.named_by == ("company Example River LLC",)
    assert record.signal.names_projects == frozenset({"milam-example-river"})


def test_a_record_that_carries_no_known_name_names_no_project():
    record = one(history(legistar("Designate a reinvestment zone"), projects=[RIVER]))
    assert record.names_projects == ()


def test_a_code_name_names_the_project():
    falcon = known("milam-example-falcon", "Milam", code_names=("Project Falcon",))
    item = "Executive session on economic development negotiations: Project Falcon"
    record = one(history(legistar(item), projects=[falcon]))
    assert record.names_projects == ("milam-example-falcon",)
    assert record.named_by == ("code name Project Falcon",)


def test_a_companys_name_counts_only_beside_the_words_data_center():
    # The list of known projects names engineers and lenders too. A rezoning that names a
    # project's engineer is not that project.
    plain = legistar("Rezone to light industrial. Applicant: Example River LLC")
    assert one(history(plain, projects=[RIVER])).names_projects == ()
    solo = known("milam-example-solo", "Milam", "Exampleco", code_names=("Cosmos",))
    quiet = legistar("Development agreement with Exampleco for the Cosmos subdivision")
    assert one(history(quiet, projects=[solo])).names_projects == ()
    direct = legistar("Development agreement with Exampleco for a data center")
    assert one(history(direct, projects=[solo])).names_projects == ("milam-example-solo",)


def test_in_a_file_the_name_must_be_near_the_words_data_center_not_near_another_term():
    filler = " ".join(["Approve the routine consent agenda and pay the bills."] * 40)
    apart = agenda_file(
        f"2. Reinvestment zone for Example River LLC. {filler} 9. Hear a data center report."
    )
    assert one(history(apart, projects=[RIVER])).names_projects == ()


def test_a_public_body_among_a_projects_companies_is_never_a_match():
    backed = known("milam-example-edc", "Milam", "Example Economic Development Corporation")
    item = "Data center update from the Example Economic Development Corporation"
    assert one(history(legistar(item), projects=[backed])).names_projects == ()
    board = known("milam-example-idc", "Milam", "Example Industrial Development Corporation")
    item = "Data center update from the Example Industrial Development Corporation"
    assert one(history(legistar(item), projects=[board])).names_projects == ()


def test_a_name_one_project_alone_carries_wins_over_a_name_two_share():
    first = known("milam-example-one", "Milam", "Example River LLC", "Example Platforms")
    second = known("milam-example-two", "Milam", "Example Platforms")
    both = one(history(legistar("Example Platforms data center update"), projects=[first, second]))
    assert both.names_projects == ("milam-example-one", "milam-example-two")
    item = "Data center abatement for Example River LLC, a unit of Example Platforms"
    alone = one(history(legistar(item), projects=[first, second]))
    assert alone.names_projects == ("milam-example-one",)


def test_in_a_long_file_a_name_counts_only_near_the_term():
    filler = " ".join(["Approve the routine consent agenda and pay the bills."] * 40)
    far = agenda_file(f"2. Plat for Example River LLC. {filler} 9. Hear a data center report.")
    assert one(history(far, projects=[RIVER])).names_projects == ()
    near = agenda_file(f"{filler} 9. Hear a data center report from Example River LLC.")
    assert one(history(near, projects=[RIVER])).names_projects == ("milam-example-river",)


def test_a_record_keeps_no_words_of_the_agenda_it_came_from():
    item = "Data center abatement for Example River LLC, presented by Pat Example"
    record = one(history(legistar(item), projects=[RIVER]))
    kept = json.dumps([record.reference, record.url, record.terms, record.named_by])
    assert "Pat Example" not in kept and "presented" not in kept


# --- projects, as the harness judges them -------------------------------------------------------


def test_a_project_gets_the_ids_of_the_parties_that_carry_its_companies_names():
    made = history(
        wells(
            {"OwnerName": "Example River, L.L.C.", "ProposedUseOtherDesc": "data center"},
            {"OwnerName": "Example River Milam LLC", "ProposedUseOtherDesc": "data center"},
            {"OwnerName": "Unrelated Data Center LLC"},
        ),
        projects=[RIVER],
    )
    (project,) = harness_projects([RIVER], made)
    ids = {r.party: r.signal.entity_id for r in made.records}
    assert project.entity_ids == frozenset(
        {ids["Example River, L.L.C."], ids["Example River Milam LLC"]}
    )
    assert project.county_fips == "48331"
    assert project.public_date == dt.date(2026, 6, 1)


# --- the agendas that were read ------------------------------------------------------------------


def test_every_agenda_read_is_kept_as_a_meeting_whether_or_not_it_gave_a_signal():
    made = history(legistar("Pay the bills"), agenda_file("2. Pay the bills."))
    assert made.records == []
    assert [(m.government, m.counties, m.day) for m in made.meetings] == [
        ("Example city", ("48331",), dt.date(2026, 3, 9)),
        ("Milam County", ("48331",), dt.date(2026, 1, 12)),
    ]
