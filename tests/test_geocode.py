"""The Census geocoder client, against three saved answers from the real service."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from collectors.base import Fetcher, LayoutChanged, LocalArchive
from pipeline.config import load_sources
from pipeline.geocode import (
    SOURCE_ID,
    ArchivedLookup,
    Geocoder,
    address_url,
    parse_address,
    parse_point,
    point_url,
)
from pipeline.store import MemorySink

from .helpers import CONTACT, FakeClock, Site

FIXTURES = Path(__file__).parent / "fixtures" / SOURCE_ID
HQ = (FIXTURES / "address-census-hq.txt").read_bytes()
NO_MATCH = (FIXTURES / "address-no-match.txt").read_bytes()
HOOD = (FIXTURES / "point-hood-county.txt").read_bytes()

HQ_ADDRESS = "4600 Silver Hill Rd, Washington, DC 20233"


def test_the_source_is_cleared_and_is_a_lookup():
    src = load_sources().by_id(SOURCE_ID)
    assert src.may_fetch_automatically and src.layer == "lookup"


def test_request_addresses_match_the_ones_the_fixtures_were_saved_from():
    assert address_url(HQ_ADDRESS) == (
        "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
        "?address=4600+Silver+Hill+Rd%2C+Washington%2C+DC+20233"
        "&benchmark=Public_AR_Current&vintage=Current_Current&layers=Counties&format=json"
    )
    assert point_url(-97.7861, 32.4421) == (
        "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
        "?x=-97.78610&y=32.44210"
        "&benchmark=Public_AR_Current&vintage=Current_Current&layers=Counties&format=json"
    )


def test_spaces_in_an_address_do_not_make_a_second_request_address():
    assert address_url("  4600  Silver Hill Rd,\nWashington, DC 20233 ") == address_url(HQ_ADDRESS)


def test_the_county_comes_from_the_point_not_the_city():
    # A Washington, DC mailing address that stands in Prince George's County, Maryland.
    out = parse_address(HQ, "u")
    assert out.status == "matched" and out.matches == 1
    assert out.county_fips == "24033"
    assert out.matched_address == "4600 SILVER HILL RD, WASHINGTON, DC, 20233"
    assert (round(out.lon, 3), round(out.lat, 3)) == (-76.928, 38.845)


def test_no_match_gives_nothing():
    out = parse_address(NO_MATCH, "u")
    assert (out.status, out.county_fips, out.lon, out.lat, out.matches) == (
        "no_match", None, None, None, 0,
    )  # fmt: skip


def test_a_point_gives_its_county():
    out = parse_point(HOOD, "u", -97.7861, 32.4421)
    assert (out.status, out.county_fips) == ("matched", "48221")


def test_two_matches_are_ambiguous_and_give_no_coordinates():
    one = HQ[HQ.index(b'"addressMatches":[') + len(b'"addressMatches":[') : -3]
    two = HQ.replace(one, one + b"," + one)
    out = parse_address(two, "u")
    assert (out.status, out.matches, out.lon, out.lat) == ("ambiguous", 2, None, None)
    assert out.county_fips == "24033"  # both matches are in the same county

    other = two.replace(b'"GEOID":"24033"', b'"GEOID":"11001"', 1)
    assert parse_address(other, "u").county_fips is None


def test_a_point_in_no_county_is_no_match():
    out = parse_point(b'{"result":{"geographies":{"Counties":[]}}}', "u", -90.0, 25.0)
    assert (out.status, out.county_fips) == ("no_match", None)


@pytest.mark.parametrize("body", [b"<html>busy</html>", b"{}", b'{"result": []}', b'{"result":{}}'])
def test_an_answer_in_another_shape_stops_the_lookup(body):
    with pytest.raises(LayoutChanged):
        parse_address(body, "u")
    with pytest.raises(LayoutChanged):
        parse_point(body, "u", 0.0, 0.0)


def test_a_point_that_is_not_a_longitude_and_latitude_is_refused():
    with pytest.raises(ValueError, match="longitude"):
        Geocoder(lambda url: HOOD).point(32.4421, -97.7861)


def test_each_question_is_asked_once_and_answered_from_the_archive_after(tmp_path):
    source = load_sources().by_id(SOURCE_ID)
    web = Site(
        {
            address_url(HQ_ADDRESS): httpx.Response(200, content=HQ),
            point_url(-97.7861, 32.4421): httpx.Response(200, content=HOOD),
        },
        robots=None,  # the service publishes no robots file
    )
    clock = FakeClock()
    store, sink = LocalArchive(tmp_path), MemorySink()
    with Fetcher(
        source, contact=CONTACT, transport=web.transport, clock=clock, sleep=clock.sleep
    ) as fetcher:
        lookup = ArchivedLookup(source, fetcher, store, sink)
        geocoder = Geocoder(lookup)
        first = geocoder.address(HQ_ADDRESS)
        again = geocoder.address(HQ_ADDRESS)
        point = geocoder.point(-97.7861, 32.4421)
        geocoder.point(-97.786100001, 32.442100001)  # the same point to five places

    assert first == again and first.county_fips == "24033"
    assert point.county_fips == "48221"
    assert lookup.requests == 2
    assert len(web.page_urls()) == 2
    # Every answer is archived with its address, time and hash.
    assert sorted(d.url for d in sink.documents.values()) == sorted(
        [address_url(HQ_ADDRESS), point_url(-97.7861, 32.4421)]
    )
    assert "DataCenterRadar" in web.requests[0].headers["user-agent"]


def test_a_lookup_needs_the_fetcher_for_its_own_source(tmp_path):
    sources = load_sources()
    with (
        Fetcher(sources.by_id("tx_ercot_rpg"), contact=CONTACT) as fetcher,
        pytest.raises(ValueError, match="different source"),
    ):
        ArchivedLookup(sources.by_id(SOURCE_ID), fetcher, LocalArchive(tmp_path), MemorySink())
