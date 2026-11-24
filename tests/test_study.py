"""Whether a company's name is a payer's name. See pipeline/study.py.

The payers are the real list, read from the saved copy of the study's page. The other names
are the real config/study_payers.yaml.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from collectors.us.qpq_data_center_payers import parse
from pipeline.config import StudyPayersFile, load_study_payers
from pipeline.study import LEGAL_FORM_ASIDE, SAME_NAME, PayerNames

FIXTURE = Path(__file__).parent / "fixtures" / "us_qpq_data_center_payers"
PAYERS = parse((FIXTURE / "data-centers-payers.html").read_bytes())
NAMES = PayerNames(PAYERS)


def met(name: str) -> tuple[str, str, str] | None:
    found = NAMES.match(name)
    return (found.payer.name, found.basis, found.matched_name) if found else None


# --- what matches -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,payer",
    [("Oncor", "Oncor"), ("ONCOR", "Oncor"), ("Google", "Google"), ("DTE Energy", "DTE Energy")],
)
def test_the_payers_name_as_it_stands(name, payer):
    assert met(name) == (payer, SAME_NAME, payer)


@pytest.mark.parametrize(
    "name,payer",
    [
        ("Google LLC", "Google"),
        ("Microsoft Corporation", "Microsoft"),
        ("DTE Energy Company", "DTE Energy"),
        ("Energy Transfer LP", "Energy Transfer"),
        ("CenterPoint Energy, Inc.", "CenterPoint Energy"),
        ("Skybox Datacenters, L.L.C.", "Skybox Datacenters"),
    ],
)
def test_the_payers_name_with_a_legal_form_at_the_end(name, payer):
    assert met(name) == (payer, LEGAL_FORM_ASIDE, payer)


@pytest.mark.parametrize(
    "name,payer,other",
    [
        ("Oncor Electric Delivery Company LLC", "Oncor", "Oncor Electric Delivery"),
        ("Georgia Power Company", "Southern Company / Georgia Power", "Georgia Power"),
        ("Consumers Energy Company", "CMS / Consumers Energy", "Consumers Energy"),
        ("Meta Platforms, Inc.", "Meta", "Meta Platforms"),
        ("Amazon.com Services LLC", "Amazon", "Amazon.com Services"),
        ("Amazon.com, Inc.", "Amazon", "Amazon.com"),
    ],
)
def test_another_name_the_study_gives_the_payer(name, payer, other):
    assert met(name) == (payer, LEGAL_FORM_ASIDE, other)


def test_a_listed_other_name_as_it_stands():
    assert met("Consumers Energy") == ("CMS / Consumers Energy", SAME_NAME, "Consumers Energy")


# --- what does not ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        # A longer name that holds a payer's name. None of these is known to be the payer.
        "Google Fiber Texas LLC",
        "Oncor Electric Delivery Administration Corp",
        "DTE Electric Company",
        "CenterPoint Energy Houston Electric LLC",
        "Vantage Data Centers TX1 LLC",
        "Amazon Data Services Inc",
        "Digital Realty Trust LP",
        # Initials are not listed.
        "CMS",
        "APS LLC",
        # Nothing to do with any payer.
        "Example Data LLC",
        "City of Granbury",
    ],
)
def test_a_longer_or_unrelated_name_meets_no_payer(name):
    assert met(name) is None


@pytest.mark.parametrize("word", ["Switch", "Meta", "Oracle", "Amazon"])
def test_an_ordinary_word_meets_its_payer_only_when_it_stands_alone(word):
    assert met(word) == (word, SAME_NAME, word)
    for form in ("LLC", "Inc.", "Ltd", "Corporation"):
        assert met(f"{word} {form}") is None


# --- the file -----------------------------------------------------------------------------------


def test_every_payer_the_file_names_is_on_the_studys_list():
    assert NAMES.unlisted == []


def test_every_ordinary_word_is_a_name_the_radar_could_meet():
    file = load_study_payers()
    usable = {p.name for p in PAYERS} | {n for e in file.other_names for n in e.names}
    assert set(file.whole_name_only) <= usable


def test_the_file_holds_no_initials_and_no_pac():
    for entry in load_study_payers().other_names:
        for name in entry.names:
            assert not (name.isupper() and len(name) <= 3), name
            assert "PAC" not in name.split() and "Committee" not in name


def file(**changes) -> StudyPayersFile:
    return StudyPayersFile.model_validate({"other_names": [], "whole_name_only": [], **changes})


def test_a_payer_the_study_no_longer_lists_is_reported_and_stops_nothing():
    names = file(other_names=[{"payer": "Gone Power", "names": ["Gone"], "where": "a test"}])
    known = PayerNames(PAYERS, names)
    assert known.unlisted == ["Gone Power"]
    assert known.match("Gone LLC") is None
    assert known.match("Oncor").payer.name == "Oncor"


def test_one_name_can_never_lead_to_two_payers():
    names = file(other_names=[{"payer": "Oncor", "names": ["Vistra"], "where": "a mistake"}])
    with pytest.raises(ValueError, match="two payers"):
        PayerNames(PAYERS, names)


def test_two_payers_that_differ_only_by_legal_form_are_refused():
    twin = dataclasses.replace(PAYERS[0], name="Dominion Energy Inc", url=PAYERS[0].url[:-1] + "0")
    with pytest.raises(ValueError, match="two payers"):
        PayerNames([*PAYERS, twin], file())


@pytest.mark.parametrize(
    "bad",
    [
        {"other_names": [{"payer": "A", "names": ["x"], "where": "w"}] * 2},
        {
            "other_names": [
                {"payer": "A", "names": ["Same"], "where": "w"},
                {"payer": "B", "names": ["same"], "where": "w"},
            ]
        },
        {"other_names": [{"payer": "A", "names": [], "where": "w"}]},
        {"other_names": [{"payer": "A", "names": ["x"]}]},
        {"whole_name_only": ["Switch", "Switch"]},
        {"whole_name_only": [" "]},
    ],
)
def test_the_file_is_checked_when_it_is_read(bad):
    with pytest.raises(ValueError):
        file(**bad)
