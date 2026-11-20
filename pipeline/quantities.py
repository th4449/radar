"""Acres, megawatts and dollars written in a text. See BUILD_PLAN.md milestone M4.

Each quantity keeps the words as written and their position. Nothing is inferred: a number
counts only when its unit is written next to it. A text can state several quantities, and this
module does not choose among them. A reviewer reads them against the source.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Kind = Literal["acres", "megawatts", "dollars"]

_NUM = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
# Do not start inside a longer number, a word or an amount of money.
_START = r"(?<![\w.,$])"
# "500 to 600 acres", "500-600 acres"
_RANGE = rf"(?:(?P<low>{_NUM})\s*(?:-|–|—|to)\s*)?(?P<num>{_NUM})"

# An acre-foot is a volume of water, not an area.
_ACRES = re.compile(
    rf"{_START}{_RANGE}\s*-?\s*(?:\+/-\s*)?acres?(?![A-Za-z])(?!-?\s?f(?:ee|oo)t)",
    re.IGNORECASE,
)

# MW and GW are matched in capitals only: mW is a milliwatt. MWh is energy, not power.
_POWER = re.compile(
    rf"{_START}{_RANGE}\s*-?\s*"
    r"(?P<unit>MW(?:ac|dc|e)?|GW|[Mm]ega[Ww]atts?|MEGAWATTS?|[Gg]iga[Ww]atts?|GIGAWATTS?)"
    r"(?![A-Za-z])(?!-?\s?h(?:ou)?rs?\b)"
)

_WORD_SCALE = {"thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
_LETTER_SCALE = {"K": 1e3, "M": 1e6, "MM": 1e6, "B": 1e9, "BN": 1e9}
_WORDS = "|".join(_WORD_SCALE)

# "$1.5 billion", "$500M", "$2,500,000"
_DOLLAR_SIGN = re.compile(
    rf"\$\s?(?P<num>{_NUM})"
    rf"(?:\s*(?P<word>{_WORDS})|(?P<letter>MM|BN|[KMB]))?(?![A-Za-z])",
    re.IGNORECASE,
)
# "40 million dollars"
_DOLLAR_WORD = re.compile(
    rf"{_START}(?P<num>{_NUM})\s*(?P<word>{_WORDS})?\s*dollars(?![A-Za-z])", re.IGNORECASE
)


@dataclass(frozen=True)
class Quantity:
    kind: Kind
    value: float  # acres, megawatts or dollars
    low: float | None  # the lower end when the text gives a range
    start: int
    end: int
    text: str  # as the source wrote it


def _number(text: str) -> float:
    return float(text.replace(",", ""))


def find_quantities(text: str) -> list[Quantity]:
    """Every acreage, power figure and dollar amount in the text, in reading order."""
    found: list[Quantity] = []

    for m in _ACRES.finditer(text):
        low = _number(m.group("low")) if m.group("low") else None
        found.append(
            Quantity("acres", _number(m.group("num")), low, m.start(), m.end(), m.group(0))
        )

    for m in _POWER.finditer(text):
        scale = 1000.0 if m.group("unit").lower().startswith("g") else 1.0
        low = _number(m.group("low")) * scale if m.group("low") else None
        found.append(
            Quantity(
                "megawatts", _number(m.group("num")) * scale, low, m.start(), m.end(), m.group(0)
            )
        )

    taken: list[tuple[int, int]] = []
    for m in _DOLLAR_SIGN.finditer(text):
        scale = 1.0
        if m.group("word"):
            scale = _WORD_SCALE[m.group("word").lower()]
        elif m.group("letter"):
            scale = _LETTER_SCALE[m.group("letter").upper()]
        found.append(
            Quantity("dollars", _number(m.group("num")) * scale, None, m.start(), m.end(),
                     m.group(0))
        )  # fmt: skip
        taken.append((m.start(), m.end()))
    for m in _DOLLAR_WORD.finditer(text):
        if any(start <= m.start() < end for start, end in taken):
            continue  # "$40 million dollars" was already read from its dollar sign
        scale = _WORD_SCALE[m.group("word").lower()] if m.group("word") else 1.0
        found.append(
            Quantity("dollars", _number(m.group("num")) * scale, None, m.start(), m.end(),
                     m.group(0))
        )  # fmt: skip

    return sorted(found, key=lambda q: (q.start, q.end))
