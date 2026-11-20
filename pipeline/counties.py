"""County assignment from names. See BUILD_PLAN.md milestone M4.

A county is assigned only from what a record says: a county column, or the words "Hood County"
in a text. A bare name is never enough in running text, because Austin is a county and a
city, and Hill and Johnson are also surnames.

For Texas the config holds only the 30 test counties. A text that names some other county is
recognized as naming one, so it can be set aside as out of scope, not mistaken for a text that
names no place at all.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pipeline.config import CountiesFile, load_counties

# "Medina County", "Tom Green County", "St. Clair County"
_ANY_COUNTY = re.compile(
    r"(?<![A-Za-z])((?:St\.? )?(?:[A-Z][a-z]+|[A-Z]{2,})(?: (?:[A-Z][a-z]+|[A-Z]{2,})){0,2})"
    r"\s+(?:County|COUNTY)(?![A-Za-z])"
)
# Capitalized words that come before "County" without being part of its name.
_NOT_A_NAME = frozenset({
    "The", "This", "That", "Each", "Any", "Every", "Our", "A", "An", "In", "Of", "Per", "Said",
    "For", "By", "With", "From", "To", "And", "Or", "Both", "All", "No", "One", "Two", "Three",
    "Four", "Five", "Six", "Other", "Another", "Same", "Which", "What", "See", "Texas",
    "Michigan", "North", "South", "East", "West", "Northern", "Southern", "Eastern", "Western",
    "Central", "Rural", "Local", "Adjacent", "Neighboring", "Multiple", "Several", "Large",
    "Load", "Project", "New",
})  # fmt: skip


@dataclass(frozen=True)
class CountyMention:
    name: str  # as configured, or as written when the county is not in the config
    fips: str | None  # None for a county outside the config
    start: int
    end: int
    text: str


class CountyIndex:
    def __init__(self, counties: CountiesFile) -> None:
        self.state = counties.state
        self._by_name = {c.name.lower(): c for c in counties.counties}
        names = sorted((re.escape(c.name) for c in counties.counties), key=len, reverse=True)
        # A space or line break between the words: PDF text breaks lines anywhere.
        alternatives = "|".join(n.replace(r"\ ", r"\s+") for n in names)
        self._known = re.compile(
            rf"(?<![A-Za-z])({alternatives})\s+County(?![A-Za-z])", re.IGNORECASE
        )

    @classmethod
    def for_state(cls, state: str) -> CountyIndex:
        return cls(load_counties(state))  # type: ignore[arg-type]

    def fips(self, name: str) -> str | None:
        """The code for a county named in a county column: "Hood", "HOOD" or "Hood County"."""
        key = " ".join(name.lower().split())
        key = key.removesuffix(" county")
        county = self._by_name.get(key)
        return county.fips if county else None

    def name(self, fips: str) -> str | None:
        for county in self._by_name.values():
            if county.fips == fips:
                return county.name
        return None

    def mentions(self, text: str) -> list[CountyMention]:
        """Every "<Name> County" in the text, in reading order."""
        found: dict[tuple[int, int], CountyMention] = {}
        for m in self._known.finditer(text):
            county = self._by_name[" ".join(m.group(1).lower().split())]
            found[(m.start(), m.end())] = CountyMention(
                county.name, county.fips, m.start(), m.end(), m.group(0)
            )
        known_ends = {end for _, end in found}
        for m in _ANY_COUNTY.finditer(text):
            if m.end() in known_ends:
                continue  # already read as a configured county
            words = m.group(1).split()
            while words and words[0].capitalize() in _NOT_A_NAME:
                words.pop(0)
            # "STEC Medina County": in mixed-case text a leading acronym is not the name.
            if any(not w.isupper() for w in words):
                while words and words[0].isupper() and words[0] not in ("St", "St."):
                    words.pop(0)
            if not words:
                continue
            name = " ".join(words)
            start = m.end(1) - len(name)
            found[(start, m.end())] = CountyMention(
                name, None, start, m.end(), text[start : m.end()]
            )
        return [found[key] for key in sorted(found)]
