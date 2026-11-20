"""Names of companies and public bodies. See BUILD_PLAN.md sections 5 and 12.

Two jobs.

Normalizing. The same company is written many ways: "Example Data, L.L.C." and "EXAMPLE DATA
LLC". canonical_name() gives one spelling for both. "Example Data LLC" and "Example Data Inc"
stay apart, because they can be different companies. match_key() drops the legal form and is
only ever a hint that two names may be related.

Holding back. The radar does not publish names of private individuals. A record's named party
is used only when the name itself shows a company or a public body. Anything else is unclear,
and an unclear party makes no signal. This errs on the side of holding back: a company whose
name carries no such word is held until a person adds it to config/entities.yaml.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

PartyKind = Literal["company", "public_body", "unclear"]

# One spelling per legal form.
_LEGAL_FORMS = {
    "LLC": "LLC", "LC": "LC", "LLP": "LLP", "LLLP": "LLLP", "LP": "LP", "PLLC": "PLLC",
    "PC": "PC", "INC": "INC", "INCORPORATED": "INC", "CORP": "CORP", "CORPORATION": "CORP",
    "CO": "CO", "COMPANY": "CO", "LTD": "LTD", "LIMITED": "LTD", "NA": "NA",
}  # fmt: skip

# These alone show a company. CO, NA, LC and PC do not: each is also a surname or initials.
_CLEAR_FORMS = frozenset(_LEGAL_FORMS) - {"CO", "NA", "LC", "PC"}

# Words that mark a private holding. They win over every other word in the name.
_PERSONAL_WORDS = frozenset({"TRUST", "TRUSTEE", "TRUSTEES", "HEIRS", "DBA", "ETAL", "ETUX"})
_PERSONAL_PHRASES = (
    "ESTATE OF", "ET AL", "ET UX", "ET VIR", "D B A", "C O", "FAMILY LP", "FAMILY LTD",
    "FAMILY LLC", "FAMILY LIMITED", "FAMILY PARTNERSHIP", "FAMILY PARTNERS", "FAMILY FARM",
    "FAMILY FARMS", "FAMILY RANCH",
)  # fmt: skip

_PUBLIC_PHRASES = (
    "CITY OF", "TOWN OF", "VILLAGE OF", "COUNTY OF", "STATE OF", "PORT OF", "UNITED STATES",
    "US ARMY", "AIR FORCE",
)  # fmt: skip
_PUBLIC_WORDS = frozenset({
    "COUNTY", "DISTRICT", "ISD", "MUD", "AUTHORITY", "DEPARTMENT", "DEPT", "COMMISSION",
    "UNIVERSITY", "COLLEGE", "MUNICIPAL", "TXDOT", "SCHOOL", "SCHOOLS", "AIRPORT", "TOWNSHIP",
})  # fmt: skip

# Ordinary words of trade. Weaker evidence than a legal form, and recorded as such.
_BUSINESS_WORDS = frozenset({
    "COMPANIES", "PARTNERS", "PARTNERSHIP", "HOLDINGS", "HOLDING", "GROUP", "ENTERPRISES",
    "ASSOCIATES", "ASSOCIATION", "ASSN", "COOPERATIVE", "COOP", "BANK", "CHURCH", "SERVICES",
    "SERVICE", "SYSTEMS", "TECHNOLOGIES", "TECHNOLOGY", "INDUSTRIES", "PROPERTIES",
    "DEVELOPMENT", "DEVELOPERS", "ENERGY", "POWER", "ELECTRIC", "UTILITIES", "UTILITY",
    "PIPELINE", "OIL", "GAS", "PETROLEUM", "MIDSTREAM", "MATERIALS", "CONSTRUCTION",
    "CONTRACTORS", "LOGISTICS", "FOUNDATION", "HOSPITAL", "RAILWAY", "RAILROAD", "AIRLINES",
    "VENTURES", "INVESTMENTS", "CAPITAL", "REALTY", "MANAGEMENT", "RESOURCES", "OPERATING",
    "OPERATIONS", "SOLUTIONS", "INTERNATIONAL", "STORES", "FOODS", "MOTORS", "AUTOMOTIVE",
    "TRUCKING", "TRANSPORTATION", "MANUFACTURING", "MFG", "CHEMICAL", "CHEMICALS", "STEEL",
    "CEMENT", "CONCRETE", "AGGREGATES", "MINING", "APARTMENTS", "HOTEL", "DATACENTER",
    "DATACENTERS", "DIGITAL", "NETWORKS", "COMMUNICATIONS", "TELECOM", "WIRELESS", "SOLAR",
    "RENEWABLES", "INFRASTRUCTURE", "REFINERY", "LANDFILL", "BUILDERS", "ENGINEERING",
    "CONSULTING", "LABORATORIES", "MEDICAL", "CLINIC",
})  # fmt: skip
_BUSINESS_PHRASES = ("DATA CENTER", "DATA CENTERS", "DATA CENTRE", "REAL ESTATE", "WATER SUPPLY")


@dataclass(frozen=True)
class Party:
    kind: PartyKind
    basis: str  # why: "legal form LLC", "public word COUNTY", "listed in config", ...

    @property
    def usable(self) -> bool:
        """True when the name may be stored in a signal."""
        return self.kind != "unclear"


def _tokens(name: str) -> list[str]:
    text = unicodedata.normalize("NFKC", name).upper().replace("&", " AND ")
    text = re.sub(r"[.'’`]", "", text)  # L.L.C. -> LLC, O'Brien -> OBRIEN
    return re.sub(r"[^A-Z0-9]+", " ", text).split()


def canonical_name(name: str) -> str:
    """One spelling for a name: capitals, no punctuation, one spelling per legal form."""
    tokens = _tokens(name)
    if tokens[:1] == ["THE"] and len(tokens) > 1:
        tokens = tokens[1:]
    # A legal form counts only at the end of a name. "CO" inside a name is just a word.
    end = len(tokens)
    while end > 1 and tokens[end - 1] in _LEGAL_FORMS:
        end -= 1
    return " ".join(tokens[:end] + [_LEGAL_FORMS[t] for t in tokens[end:]])


def match_key(name: str) -> str:
    """The canonical name without its legal form. A hint, never proof of the same company."""
    tokens = canonical_name(name).split()
    while len(tokens) > 1 and tokens[-1] in _LEGAL_FORMS.values():
        tokens.pop()
    return " ".join(tokens)


def _has_phrase(joined: str, phrases: tuple[str, ...]) -> str | None:
    padded = f" {joined} "
    for phrase in phrases:
        if f" {phrase} " in padded:
            return phrase
    return None


def classify_party(name: str, known: frozenset[str] = frozenset()) -> Party:
    """Whether a name shows a company or a public body. `known` holds canonical names."""
    tokens = _tokens(name)
    if not tokens:
        return Party("unclear", "no name")
    joined = " ".join(tokens)
    words = set(tokens)

    phrase = _has_phrase(joined, _PERSONAL_PHRASES)
    if phrase:
        return Party("unclear", f"personal phrase {phrase}")
    personal = sorted(words & _PERSONAL_WORDS)
    if personal:
        return Party("unclear", f"personal word {personal[0]}")

    if canonical_name(name) in known:
        return Party("company", "listed in config")
    if len(tokens) > 1 and tokens[-1] in _CLEAR_FORMS:
        return Party("company", f"legal form {_LEGAL_FORMS[tokens[-1]]}")
    phrase = _has_phrase(joined, _PUBLIC_PHRASES)
    if phrase:
        return Party("public_body", f"public phrase {phrase}")
    public = sorted(words & _PUBLIC_WORDS)
    if public:
        return Party("public_body", f"public word {public[0]}")
    phrase = _has_phrase(joined, _BUSINESS_PHRASES)
    if phrase:
        return Party("company", f"business phrase {phrase}")
    business = sorted(words & _BUSINESS_WORDS)
    if business:
        return Party("company", f"business word {business[0]}")
    return Party("unclear", "no word that shows a company or public body")


# One to six capitalized words and then a legal form that alone shows a company.
_COMPANY_IN_TEXT = re.compile(
    r"(?<![A-Za-z])((?:[A-Z][A-Za-z0-9&.'’-]*,?[ \t]+){1,6}?"
    r"(?:LLC|L\.L\.C\.|Inc\.?|Incorporated|Corp\.?|Corporation|LP|L\.P\.|LLP|Ltd\.?))"
    r"(?![A-Za-z])"
)


def find_companies(text: str) -> list[str]:
    """Company names written out with a legal form, as the text writes them, once each.

    Only a help for the reader. A name at the start of a sentence can pick up the word before
    it, and a company written without its legal form is not found.
    """
    found: list[str] = []
    for m in _COMPANY_IN_TEXT.finditer(text):
        name = " ".join(m.group(1).split()).rstrip(".")
        if classify_party(name).usable and name not in found:
            found.append(name)
    return found
