"""Company names: one spelling, and the rule that holds back names of people."""

from __future__ import annotations

import pytest

from pipeline.config import load_entities
from pipeline.entities import canonical_name, classify_party, match_key

KNOWN = frozenset(canonical_name(n) for n in load_entities().known_organizations)


@pytest.mark.parametrize(
    ("written", "canonical"),
    [
        ("Example Data, L.L.C.", "EXAMPLE DATA LLC"),
        ("EXAMPLE DATA LLC", "EXAMPLE DATA LLC"),
        ("The Example Company", "EXAMPLE CO"),
        ("Example & Sons Incorporated", "EXAMPLE AND SONS INC"),
        ("Example Power Corporation", "EXAMPLE POWER CORP"),
        ("  example   data ,  llc ", "EXAMPLE DATA LLC"),
        ("Amazon.Com Services LLC", "AMAZONCOM SERVICES LLC"),
        ("O'Example Holdings, L.P.", "OEXAMPLE HOLDINGS LP"),
        ("Example Co Operating LLC", "EXAMPLE CO OPERATING LLC"),
    ],
)
def test_canonical_name(written, canonical):
    assert canonical_name(written) == canonical


def test_different_legal_forms_stay_different_companies():
    assert canonical_name("Example Data LLC") != canonical_name("Example Data Inc")
    assert match_key("Example Data LLC") == match_key("Example Data, Inc.") == "EXAMPLE DATA"


def test_match_key_never_empties_a_name():
    assert match_key("Company") == "COMPANY"
    assert match_key("LLC") == "LLC"


@pytest.mark.parametrize(
    "name",
    [
        "NTT Global Data Centers AUI, LLC",
        "CyrusOne Bosque LLC",
        "Amazon.Com Services LLC",
        "Crusoe Energy Systems, LLC",
        "Example Holdings LP",
        "Example Power Corporation",
        "Example Electric Cooperative",
        "Example Data Center",
        "Example Real Estate",
    ],
)
def test_a_name_that_shows_a_company_is_usable(name):
    party = classify_party(name)
    assert party.kind == "company" and party.usable


@pytest.mark.parametrize(
    "name",
    [
        "City of Stanton",
        "Hood County",
        "Example Independent School District",
        "Example Municipal Utility District No. 4",
        "Texas Department of Transportation",
        "Lower Example River Authority",
    ],
)
def test_a_public_body_is_usable(name):
    party = classify_party(name)
    assert party.kind == "public_body" and party.usable


@pytest.mark.parametrize(
    "name",
    [
        "INVENTED HOUSEHOLD OWNER",
        "Doe, Jane",
        "John Q Example",
        "J & M Example",
        "Example Ranch",
        "Example Farms",
        "",
        "   ",
    ],
)
def test_a_name_with_no_such_word_is_held_back(name):
    party = classify_party(name)
    assert party.kind == "unclear" and not party.usable


@pytest.mark.parametrize(
    "name",
    [
        "Jane Example Living Trust",
        "Estate of John Example",
        "John Example DBA Example Drilling Services",
        "John Example et ux",
        "Example Family Partnership LP",
        "Jane Example, Trustee",
        "Example Properties c/o Jane Example",
    ],
)
def test_a_private_holding_is_held_back_even_with_a_company_word(name):
    assert classify_party(name).kind == "unclear"


@pytest.mark.parametrize("name", ["John Co", "Jane Na", "Example PC"])
def test_short_forms_that_are_also_surnames_do_not_show_a_company(name):
    assert classify_party(name).kind == "unclear"


def test_real_estate_is_not_an_estate():
    assert classify_party("Example Real Estate LLC").kind == "company"


def test_a_listed_company_is_usable_and_a_longer_name_is_not_matched():
    assert classify_party("GOOGLE").kind == "unclear"
    assert classify_party("GOOGLE", KNOWN) == classify_party("google", KNOWN)
    assert classify_party("Google", KNOWN).basis == "listed in config"
    assert classify_party("Meta Example", KNOWN).kind == "unclear"


def test_the_basis_says_why():
    assert classify_party("Example Data LLC").basis == "legal form LLC"
    assert classify_party("City of Example").basis == "public phrase CITY OF"
    assert classify_party("Example Energy").basis == "business word ENERGY"
    assert classify_party("Jane Example Trust").basis == "personal word TRUST"


def test_the_config_list_holds_no_duplicates_after_normalizing():
    names = load_entities().known_organizations
    assert len({canonical_name(n) for n in names}) == len(names)
