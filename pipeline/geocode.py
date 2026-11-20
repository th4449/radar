"""The Census Bureau geocoder. See docs/sources/us_census_geocoder.md.

Two questions: where is this address, and which county holds this point. The county always
comes from the point, never from the city in the address. The Census Bureau's own headquarters
has a Washington, DC mailing address and stands in Prince George's County, Maryland.

The geocoder places an address along a street's address range, so its coordinates are
approximate. An address with more than one match is ambiguous and gets no coordinates.

Never send the geocoder a record that names a person. The caller checks that first.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlencode

from collectors.base import ArchiveStore, Fetcher, LayoutChanged, Sink, archive
from pipeline.config import Source

SOURCE_ID = "us_census_geocoder"
BASE = "https://geocoding.geo.census.gov/geocoder/geographies"
_COMMON = {
    "benchmark": "Public_AR_Current",
    "vintage": "Current_Current",
    "layers": "Counties",
    "format": "json",
}

Status = Literal["matched", "no_match", "ambiguous"]


@dataclass(frozen=True)
class Located:
    status: Status
    county_fips: str | None
    lon: float | None
    lat: float | None
    matched_address: str | None  # as the geocoder wrote it
    matches: int
    url: str  # the request, so the answer can be found in the archive


def address_url(address: str) -> str:
    return f"{BASE}/onelineaddress?" + urlencode({"address": " ".join(address.split()), **_COMMON})


def point_url(lon: float, lat: float) -> str:
    # Five decimal places is about one meter, and keeps the same point at the same address.
    return f"{BASE}/coordinates?" + urlencode({"x": f"{lon:.5f}", "y": f"{lat:.5f}", **_COMMON})


def _result(body: bytes) -> dict:
    try:
        result = json.loads(body)["result"]
    except (ValueError, KeyError, TypeError) as exc:
        raise LayoutChanged("the geocoder's answer is not the JSON it documents") from exc
    if not isinstance(result, dict):
        raise LayoutChanged("the geocoder's answer has no result")
    return result


def _county(geographies: object) -> str | None:
    """The county code, when the answer names exactly one county."""
    counties = geographies.get("Counties") if isinstance(geographies, dict) else None
    if not isinstance(counties, list) or len(counties) != 1:
        return None
    geoid = str(counties[0].get("GEOID", ""))
    return geoid if len(geoid) == 5 and geoid.isdigit() else None


def parse_address(body: bytes, url: str) -> Located:
    matches = _result(body).get("addressMatches")
    if not isinstance(matches, list):
        raise LayoutChanged("the geocoder's answer has no list of matches")
    if not matches:
        return Located("no_match", None, None, None, None, 0, url)
    counties = {_county(m.get("geographies")) for m in matches}
    shared = counties.pop() if len(counties) == 1 else None
    if len(matches) > 1:
        return Located("ambiguous", shared, None, None, None, len(matches), url)
    match = matches[0]
    point = match.get("coordinates") or {}
    try:
        lon, lat = float(point["x"]), float(point["y"])
    except (KeyError, TypeError, ValueError) as exc:
        raise LayoutChanged("a match has no coordinates") from exc
    return Located("matched", shared, lon, lat, match.get("matchedAddress"), 1, url)


def parse_point(body: bytes, url: str, lon: float, lat: float) -> Located:
    result = _result(body)
    if "geographies" not in result:
        raise LayoutChanged("the geocoder's answer has no geographies")
    county = _county(result["geographies"])
    return Located("matched" if county else "no_match", county, lon, lat, None, int(bool(county)),
                   url)  # fmt: skip


class ArchivedLookup:
    """Ask a URL once, archive the answer and answer from the archive after that.

    Requests go through the same fetcher as every collector, so the pace, the user agent and a
    refusal are handled the same way.
    """

    def __init__(self, source: Source, fetcher: Fetcher, store: ArchiveStore, sink: Sink) -> None:
        if source.id != fetcher.source.id:
            raise ValueError("the fetcher is bound to a different source")
        self._source, self._fetcher, self._store, self._sink = source, fetcher, store, sink
        self.requests = 0

    def __call__(self, url: str) -> bytes:
        held = self._sink.find(self._source, url)
        if held is not None:
            return self._store.get(held.storage_path)
        result = self._fetcher.get(url)
        self.requests += 1
        self._sink.save_document(archive(result, self._source, self._store))
        return result.body


class Geocoder:
    def __init__(self, lookup: Callable[[str], bytes]) -> None:
        self._lookup = lookup

    def address(self, address: str) -> Located:
        """Where a street address is. The address needs a number and a street."""
        url = address_url(address)
        return parse_address(self._lookup(url), url)

    def point(self, lon: float, lat: float) -> Located:
        """Which county holds a point."""
        if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
            raise ValueError("not a longitude and latitude")
        url = point_url(lon, lat)
        return parse_point(self._lookup(url), url, lon, lat)
