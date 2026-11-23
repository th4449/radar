"""Which signals are one site. Synthetic signals, written before the clustering code."""

from __future__ import annotations

import datetime as dt

from pipeline.cluster import Group, Item, assign, distance_m
from pipeline.config import load_scoring

RULES = load_scoring().clustering  # near 1,000 m, same company 5,000 m
HOOD, BOSQUE = "48221", "48035"
DAY = dt.date(2026, 6, 1)

# Granbury, and points about 500 m, 3 km and 11 km east of it.
HERE = (-97.7861, 32.4421)
NEAR = (-97.7808, 32.4421)
SAME_AREA = (-97.7541, 32.4421)
FAR = (-97.6690, 32.4421)


def item(
    signal_id: int,
    county: str = HOOD,
    entity: int | None = None,
    point: tuple[float, float] | None = None,
    names: tuple[str, ...] = (),
    day: int = 0,
    meeting: str | None = None,
) -> Item:
    when = DAY + dt.timedelta(days=day)
    return Item(signal_id, county, entity, point, frozenset(names), when, meeting)


def sites_of(plan) -> list[list[int]]:
    """The signal ids of each site in the plan, new and existing, each sorted."""
    by_site: dict[object, list[int]] = {}
    for signal_id, key in plan.attach.items():
        by_site.setdefault(key, []).append(signal_id)
    return sorted(sorted(ids) for ids in by_site.values())


def test_the_test_points_are_where_the_tests_say():
    assert 400 < distance_m(HERE, NEAR) < 600
    assert 2500 < distance_m(HERE, SAME_AREA) < 3500
    assert 10000 < distance_m(HERE, FAR) < 12000
    assert distance_m(HERE, HERE) == 0


# --- one company --------------------------------------------------------------------------------


def test_signals_naming_one_company_in_one_county_are_one_site():
    plan = assign([item(i, entity=7) for i in range(1, 17)], [], RULES)
    assert sites_of(plan) == [list(range(1, 17))]
    assert len(plan.new_sites) == 1


def test_the_same_company_in_another_county_is_another_site():
    plan = assign([item(1, HOOD, entity=7), item(2, BOSQUE, entity=7)], [], RULES)
    assert sites_of(plan) == [[1], [2]]


def test_the_same_company_far_apart_in_one_county_is_two_sites():
    plan = assign([item(1, entity=7, point=HERE), item(2, entity=7, point=FAR)], [], RULES)
    assert sites_of(plan) == [[1], [2]]


def test_the_same_company_a_few_kilometers_apart_is_one_site():
    plan = assign([item(1, entity=7, point=HERE), item(2, entity=7, point=SAME_AREA)], [], RULES)
    assert sites_of(plan) == [[1, 2]]


def test_a_signal_with_no_coordinates_joins_its_company_s_site():
    plan = assign([item(1, entity=7, point=HERE), item(2, entity=7)], [], RULES)
    assert sites_of(plan) == [[1, 2]]


# --- different companies ------------------------------------------------------------------------


def test_two_companies_at_the_same_place_are_one_site():
    plan = assign([item(1, entity=7, point=HERE), item(2, entity=8, point=NEAR)], [], RULES)
    assert sites_of(plan) == [[1, 2]]
    assert plan.reasons[2] == "coordinates within 1000 m"


def test_two_companies_a_few_kilometers_apart_are_two_sites():
    plan = assign([item(1, entity=7, point=HERE), item(2, entity=8, point=SAME_AREA)], [], RULES)
    assert sites_of(plan) == [[1], [2]]


def test_two_companies_with_no_coordinates_are_two_sites():
    plan = assign([item(1, entity=7), item(2, entity=8)], [], RULES)
    assert sites_of(plan) == [[1], [2]]


def test_nearness_never_crosses_a_county_line():
    plan = assign([item(1, HOOD, point=HERE), item(2, BOSQUE, point=HERE)], [], RULES)
    assert sites_of(plan) == [[1], [2]]


# --- names --------------------------------------------------------------------------------------


def test_a_shared_code_name_or_project_number_is_one_site():
    plan = assign(
        [item(1, names=("Project Toaster",)), item(2, names=("Project Toaster", "25RPG020"))],
        [],
        RULES,
    )
    assert sites_of(plan) == [[1, 2]]
    assert plan.reasons[2] == "the same project name or number"


def test_the_same_code_name_in_another_county_is_another_site():
    plan = assign(
        [item(1, HOOD, names=("Project Toaster",)), item(2, BOSQUE, names=("Project Toaster",))],
        [],
        RULES,
    )
    assert sites_of(plan) == [[1], [2]]


def test_links_chain():
    # 1 and 3 share nothing. 2 shares a company with 1 and a place with 3.
    plan = assign(
        [
            item(1, entity=7),
            item(2, entity=7, point=HERE, day=1),
            item(3, entity=8, point=NEAR, day=2),
        ],
        [],
        RULES,
    )
    assert sites_of(plan) == [[1, 2, 3]]


# --- a signal with nothing to hold it -----------------------------------------------------------


def test_a_signal_with_no_company_place_or_name_makes_no_site():
    plan = assign([item(1), item(2, entity=7)], [], RULES)
    assert plan.unanchored == [1]
    assert sites_of(plan) == [[2]]


# --- an agenda that says "data center" -----------------------------------------------------------

COURT = "Example County, meeting of June 8, 2026"


def test_an_agenda_record_held_to_its_meeting_makes_a_site():
    """The backtest of November 23, 2026 found one record that came before a project was
    public: a county agenda. It named no company the radar could keep, so it sat on no site
    and no reviewer would have seen it. The owner approved this way onto a site."""
    plan = assign([item(1, meeting=COURT)], [], RULES)
    assert plan.unanchored == []
    assert sites_of(plan) == [[1]]


def test_records_of_one_meeting_are_one_site_and_another_meeting_is_another():
    later = "Example County, meeting of June 22, 2026"
    plan = assign(
        [item(1, meeting=COURT), item(2, meeting=COURT), item(3, meeting=later, day=14)],
        [],
        RULES,
    )
    assert sites_of(plan) == [[1, 2], [3]]
    assert plan.reasons[2] == "the same meeting's agenda"


def test_the_same_words_for_a_meeting_in_another_county_are_another_site():
    plan = assign([item(1, HOOD, meeting=COURT), item(2, BOSQUE, meeting=COURT)], [], RULES)
    assert sites_of(plan) == [[1], [2]]


def test_a_meeting_does_not_pull_in_a_signal_with_nothing_to_hold_it():
    plan = assign([item(1, meeting=COURT), item(2)], [], RULES)
    assert plan.unanchored == [2]
    assert sites_of(plan) == [[1]]


# --- sites that already exist -------------------------------------------------------------------


def test_a_new_signal_joins_the_site_that_already_holds_its_company():
    existing = [Group(41, HOOD, [item(1, entity=7, point=HERE)])]
    plan = assign([item(2, entity=7, day=30), item(3, entity=9, day=30)], existing, RULES)
    assert plan.attach[2] == 41
    assert plan.reasons[2] == "the same company"
    assert [g.members[0].signal_id for g in plan.new_sites] == [3]


def test_signals_already_on_a_site_are_never_moved():
    existing = [
        Group(41, HOOD, [item(1, entity=7)]),
        Group(42, HOOD, [item(2, entity=7)]),  # a person split these, or an older rule did
    ]
    plan = assign([], existing, RULES)
    assert plan.attach == {} and plan.new_sites == []


def test_a_signal_that_fits_two_sites_joins_the_older_and_both_are_flagged():
    existing = [
        Group(42, HOOD, [item(2, entity=8, point=NEAR)]),
        Group(41, HOOD, [item(1, entity=7)]),
    ]
    plan = assign([item(3, entity=7, point=HERE)], existing, RULES)
    assert plan.attach[3] == 41
    assert plan.possible_same_site == [(3, [41, 42])]


def test_a_new_signal_does_not_join_a_site_in_another_county():
    existing = [Group(41, BOSQUE, [item(1, BOSQUE, entity=7)])]
    plan = assign([item(2, HOOD, entity=7)], existing, RULES)
    assert plan.attach[2] != 41 and len(plan.new_sites) == 1


# --- the same answer every time -----------------------------------------------------------------


def test_the_order_signals_arrive_in_does_not_change_the_sites():
    items = [
        item(1, entity=7, point=HERE, day=0),
        item(2, entity=7, day=1),
        item(3, entity=8, point=NEAR, day=2),
        item(4, entity=9, point=FAR, day=3),
        item(5, BOSQUE, entity=7, day=4),
        item(6, names=("Project Toaster",), day=5),
        item(7, names=("Project Toaster",), point=FAR, day=6),
        item(8, day=7),
    ]
    expected = sites_of(assign(items, [], RULES))
    assert expected == [[1, 2, 3], [4, 6, 7], [5]]
    orders = [items[n:] + items[:n] for n in range(len(items))]
    for order in [*orders, *(o[::-1] for o in orders)]:
        plan = assign(order, [], RULES)
        assert sites_of(plan) == expected
        assert plan.unanchored == [8]


def test_new_sites_come_out_oldest_signal_first():
    plan = assign([item(2, entity=8, day=5), item(1, entity=7, day=1)], [], RULES)
    assert [g.members[0].signal_id for g in plan.new_sites] == [1, 2]
