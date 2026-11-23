"""The files in config/ load, and the decisions in BUILD_PLAN.md hold."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from pipeline import config

REPO = Path(__file__).resolve().parent.parent

RANKED_25 = {
    "Hood", "Hill", "Potter", "Archer", "Somervell", "Henderson", "Austin", "Tom Green",
    "Lubbock", "Parker", "Wise", "Erath", "Bosque", "Johnson", "Ellis", "Carson", "Callahan",
    "San Saba", "Burnet", "Milam", "Freestone", "Falls", "Matagorda", "Hopkins", "Bowie",
}  # fmt: skip
ACTIVITY_5 = {"Dallas", "Taylor", "Bexar", "Travis", "Harris"}
MI_FIRST = {"Washtenaw", "Wayne", "Oakland", "Monroe", "Allegan", "Kalamazoo"}


def test_texas_has_the_30_counties_in_the_plan():
    tx = config.load_counties("TX")
    assert len(tx.counties) == 30
    assert {c.name for c in tx.counties if c.group == "ranked_25"} == RANKED_25
    assert {c.name for c in tx.counties if c.group == "activity_5"} == ACTIVITY_5


def test_texas_fips_spot_checks():
    # Known codes, checked against the Census county file.
    by_name = {c.name: c.fips for c in config.load_counties("TX").counties}
    assert by_name["Harris"] == "48201"
    assert by_name["Dallas"] == "48113"
    assert by_name["Travis"] == "48453"
    assert by_name["Bexar"] == "48029"
    assert by_name["Hood"] == "48221"


def test_michigan_has_83_counties_and_six_first():
    mi = config.load_counties("MI")
    assert len(mi.counties) == 83
    assert {c.name for c in mi.counties if c.agenda_priority == 1} == MI_FIRST
    by_name = {c.name: c.fips for c in mi.counties}
    assert by_name["Wayne"] == "26163"
    assert by_name["Washtenaw"] == "26161"


def test_every_source_is_manual_until_verified():
    """Nothing is automated before its terms and robots rules are written up."""
    sources = config.load_sources().sources
    assert len(sources) >= 20
    for s in sources:
        note = REPO / "docs" / "sources" / f"{s.id}.md"
        if s.verified_at is not None:
            assert note.exists(), f"{s.id} is marked verified but has no source note"
        if s.may_fetch_automatically:
            assert s.verified_at is not None
            assert s.robots_status == "allowed"
            assert note.exists()


def test_source_cannot_be_automated_without_verification():
    base = dict(
        id="tx_example",
        state="TX",
        name="Example",
        url="https://example.gov/x",
        layer="signal",
        intended_method="http",
        cadence="daily",
        notes="",
    )
    with pytest.raises(ValidationError):
        config.Source(**base, method="http", robots_status="allowed", verified_at=None)
    with pytest.raises(ValidationError):
        config.Source(
            **base, method="http", robots_status="restricted", verified_at=dt.date(2026, 11, 19)
        )
    ok = config.Source(
        **base, method="http", robots_status="allowed", verified_at=dt.date(2026, 11, 19)
    )
    assert ok.may_fetch_automatically


def test_only_a_manual_source_can_be_saved_by_hand():
    base = dict(
        id="tx_example",
        state="TX",
        name="Example",
        url="https://example.gov/x",
        layer="baseline",
        intended_method="http",
        cadence="monthly",
        notes="",
        verified_at=dt.date(2026, 11, 19),
        hand_saved=True,
    )
    with pytest.raises(ValidationError, match="hand_saved"):
        config.Source(**base, method="http", robots_status="allowed")
    kept = config.Source(**base, method="manual", robots_status="blocked")
    assert kept.hand_saved and not kept.may_fetch_automatically
    # One source is marked so today: the owner's decision of November 23, 2026.
    marked = {s.id for s in config.load_sources().sources if s.hand_saved}
    assert marked == {"tx_comptroller_data_centers"}


def test_source_rejects_unknown_keys():
    with pytest.raises(ValidationError):
        config.SourcesFile.model_validate({"sources": [], "extra": 1})


def test_the_words_for_a_governments_own_computers_do_not_overlap_the_words_for_a_project():
    own = config.load_keywords().own_computers
    assert own.shows and own.unless
    assert not set(own.shows) & set(own.unless)
    for word in (*own.shows, *own.unless):
        assert word == word.lower().strip()
    with pytest.raises(ValidationError):
        config.OwnComputers(shows=["Servers"], unless=["abatement"])
    with pytest.raises(ValidationError):
        config.OwnComputers(shows=["servers"], unless=["servers"])


def test_keywords_cover_the_plan_list():
    kw = config.load_keywords()
    assert "data center" in kw.direct_terms
    for term in (
        "light industrial",
        "data processing",
        "technology campus",
        "development agreement",
        "large load",
        "reinvestment zone",
        "special land use",
    ):
        assert term in kw.code_words
    pat = re.compile(kw.project_code_name.pattern)
    assert pat.search("Consider Project Falcon incentives").group(1) == "Falcon"
    assert pat.search("the project manager reported") is None


def test_scoring_matches_the_plan_placeholders():
    sc = config.load_scoring()
    assert sc.placeholder is True
    weights = {name: st.weight for name, st in sc.signal_types.items()}
    assert weights == {
        "abatement_notice": "high",
        "air_permit": "high",
        "transmission_filing": "high",
        "commission_docket": "high",
        "well_report": "medium",
        "stormwater_notice": "medium",
        "entity_land_purchase": "low",
        "agenda_keyword": "low",
    }
    assert sc.multi_signal_bonus.min_signal_types == 2
    assert sc.multi_signal_bonus.window_days == 365


def test_scoring_rejects_a_medium_signal_that_outscores_a_high_one():
    data = config.load_scoring().model_dump()
    data["signal_types"]["well_report"]["points"] = 99
    with pytest.raises(ValidationError):
        config.ScoringFile.model_validate(data)


def test_confidence_names_every_rule_and_a_direct_term_is_the_surest():
    sc = config.load_scoring()
    assert set(sc.confidence) == set(config.RULES)
    assert sc.confidence["direct_term"] == max(sc.confidence.values())
    assert sc.confidence["listed_company_loose"] < sc.confidence["listed_company"]

    data = sc.model_dump()
    data["confidence"]["code_word"] = 0.95
    with pytest.raises(ValidationError):
        config.ScoringFile.model_validate(data)
    data = sc.model_dump()
    del data["confidence"]["code_word"]
    with pytest.raises(ValidationError):
        config.ScoringFile.model_validate(data)


def test_the_lists_that_name_people_are_marked():
    marked = {s.id for s in config.load_sources().sources if s.personal_rows}
    # Two lists of applicants and owners, and meeting agendas, which name staff and applicants.
    # Building registrations name an owner and an architect. That source is proposed, not read.
    assert marked == {
        "tx_tceq_air_pending_legacy",
        "tx_twdb_well_reports",
        "tx_agendas_legistar",
        "tx_agendas_own_sites",
        "tx_tdlr_building_registrations",
    }


def test_the_reference_list_of_texas_counties_does_not_change_the_scope():
    assert len(config.load_counties("TX").counties) == 30
    assert len(config.load_all_counties("TX").counties) == 254
    assert len(config.load_all_counties("MI").counties) == 83
