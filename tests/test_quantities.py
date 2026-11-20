"""Acres, megawatts and dollars: only what the text states, with its unit."""

from __future__ import annotations

from pipeline.quantities import find_quantities


def found(text: str) -> list[tuple[str, float, float | None]]:
    return [(q.kind, q.value, q.low) for q in find_quantities(text)]


def test_acres():
    assert found("a 1,200 acre tract") == [("acres", 1200.0, None)]
    assert found("approximately 312.5 acres") == [("acres", 312.5, None)]
    assert found("the 600-acre site") == [("acres", 600.0, None)]
    assert found("ACRES: 40 Acres") == [("acres", 40.0, None)]


def test_a_range_keeps_both_ends():
    assert found("between 500 to 600 acres") == [("acres", 600.0, 500.0)]
    assert found("300-400 MW of load") == [("megawatts", 400.0, 300.0)]


def test_acre_feet_is_water_not_land():
    assert found("pumping 300 acre-feet per year") == []
    assert found("1,500 acre feet") == []


def test_megawatts_and_gigawatts():
    assert found("a 300 MW load") == [("megawatts", 300.0, None)]
    assert found("up to 1.2 GW") == [("megawatts", 1200.0, None)]
    assert found("450 megawatts at full build") == [("megawatts", 450.0, None)]
    assert found("a 250-MW substation") == [("megawatts", 250.0, None)]
    assert found("2 gigawatts") == [("megawatts", 2000.0, None)]


def test_energy_and_milliwatts_are_not_power():
    assert found("500 MWh of storage") == []
    assert found("500 MW-hr") == []
    assert found("500 MW hours") == []
    assert found("a 5 mW laser") == []


def test_power_followed_by_an_ordinary_word():
    assert found("the 500 MW has been studied") == [("megawatts", 500.0, None)]


def test_dollars():
    assert found("an investment of $1.5 billion") == [("dollars", 1.5e9, None)]
    assert found("$500 million in equipment") == [("dollars", 5e8, None)]
    assert found("valued at $2,500,000.") == [("dollars", 2.5e6, None)]
    assert found("$750M and $3B and $10K and $2MM") == [
        ("dollars", 7.5e8, None), ("dollars", 3e9, None), ("dollars", 1e4, None),
        ("dollars", 2e6, None),
    ]  # fmt: skip
    assert found("40 million dollars") == [("dollars", 4e7, None)]


def test_a_dollar_amount_is_read_once():
    assert found("$40 million dollars") == [("dollars", 4e7, None)]
    assert found("$ 40 million dollars") == [("dollars", 4e7, None)]


def test_a_number_without_its_unit_is_not_a_quantity():
    assert found("Section 12, Block 300, permit 4500") == []
    assert found("300 parking spaces and 12 buildings") == []


def test_part_of_a_longer_number_is_never_read_alone():
    assert found("12,300 acres") == [("acres", 12300.0, None)]
    assert found("1.25 MW") == [("megawatts", 1.25, None)]


def test_each_quantity_keeps_its_words_and_place():
    text = "The 600-acre campus would draw 1.2 GW and cost $3 billion."
    out = find_quantities(text)
    assert [q.text for q in out] == ["600-acre", "1.2 GW", "$3 billion"]
    assert all(text[q.start : q.end] == q.text for q in out)
