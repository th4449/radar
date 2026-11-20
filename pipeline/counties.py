"""County assignment from names. See BUILD_PLAN.md milestone M4.

A county is assigned only from what a record says: a county column, the words "Hood County"
in a text, or a list such as "Bexar and Medina counties". A bare name is never enough in
running text, because Austin is a county and a city, and Hill and Johnson are also surnames.

Texas has 254 counties and the radar's scope is 30 of them. Every county is recognized, so a
text about some other county is set aside as out of scope, not mistaken for a text that names
no place.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pipeline.config import CountiesFile, load_all_counties, load_counties


@dataclass(frozen=True)
class CountyMention:
    name: str  # as the Census Bureau writes it
    fips: str
    in_scope: bool  # one of the counties the radar covers
    start: int
    end: int
    text: str


class CountyIndex:
    def __init__(self, scope: CountiesFile, every: CountiesFile | None = None) -> None:
        every = every or scope
        self.state = scope.state
        self._scope = {c.fips for c in scope.counties}
        self._by_name = {c.name.lower(): c for c in every.counties}
        if not self._scope <= {c.fips for c in every.counties}:
            raise ValueError("a county in scope is missing from the full list")
        names = sorted((re.escape(c.name) for c in every.counties), key=len, reverse=True)
        # A space or line break between the words: PDF text breaks lines anywhere.
        one = "(?:" + "|".join(n.replace(r"\ ", r"\s+") for n in names) + ")"
        self._name = re.compile(rf"(?<![A-Za-z]){one}(?![A-Za-z])", re.IGNORECASE)
        self._single = re.compile(rf"(?<![A-Za-z])({one})\s+County(?![A-Za-z])", re.IGNORECASE)
        # "Bexar and Medina counties", "Hood, Somervell, and Erath Counties"
        self._several = re.compile(
            rf"(?<![A-Za-z])({one}(?:\s*,\s*{one})*\s*,?\s+(?:and|&)\s+{one})\s+Counties(?![A-Za-z])",
            re.IGNORECASE,
        )

    @classmethod
    def for_state(cls, state: str) -> CountyIndex:
        return cls(load_counties(state), load_all_counties(state))  # type: ignore[arg-type]

    def _county(self, written: str):
        return self._by_name.get(" ".join(written.lower().split()).removesuffix(" county"))

    def fips(self, name: str) -> str | None:
        """The code for a county in scope, named in a county column: "Hood" or "Hood County"."""
        county = self._county(name)
        return county.fips if county and county.fips in self._scope else None

    def lookup(self, name: str) -> tuple[str, str, bool] | None:
        """A county by name, in scope or not: its name, its code and whether it is in scope."""
        county = self._county(name)
        return (county.name, county.fips, county.fips in self._scope) if county else None

    def name(self, fips: str) -> str | None:
        for county in self._by_name.values():
            if county.fips == fips:
                return county.name
        return None

    def _mention(self, text: str, start: int, end: int, written: str) -> CountyMention:
        county = self._county(written)
        return CountyMention(
            county.name, county.fips, county.fips in self._scope, start, end, text[start:end]
        )

    def mentions(self, text: str) -> list[CountyMention]:
        """Every county the text names as a county, in reading order."""
        found: dict[int, CountyMention] = {}
        for m in self._single.finditer(text):
            found[m.start()] = self._mention(text, m.start(), m.end(), m.group(1))
        for m in self._several.finditer(text):
            for name in self._name.finditer(text, m.start(1), m.end(1)):
                found.setdefault(
                    name.start(), self._mention(text, name.start(), name.end(), name.group(0))
                )
        return [found[start] for start in sorted(found)]
