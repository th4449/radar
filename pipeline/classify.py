"""Keyword rules. See BUILD_PLAN.md section 6 and config/keywords.yaml.

A hit says only that a term appears in a text, and where. It is a weak signal by itself: most
light industrial rezonings are warehouses. Every hit keeps the words as the source wrote them
and their position, so a reviewer can find them in the archived record.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from pipeline.config import KeywordsFile, load_keywords

Kind = Literal["direct_term", "code_word", "project_code_name"]

# Between the words of a term: spaces, a line break or a hyphen. PDF text breaks lines anywhere.
_GAP = r"[\s\-‐-―]+"
_WORD_CHAR = "A-Za-z0-9"


@dataclass(frozen=True)
class Hit:
    kind: Kind
    term: str  # the configured term, or the code name written as "Project Falcon"
    start: int
    end: int
    text: str  # as the source wrote it


def _term_pattern(term: str) -> re.Pattern[str]:
    body = _GAP.join(re.escape(word) for word in term.split())
    # Whole words only, with a plural allowed: "data centers", "technology campuses".
    return re.compile(rf"(?<![{_WORD_CHAR}]){body}(?:e?s)?(?![{_WORD_CHAR}])", re.IGNORECASE)


class KeywordRules:
    """The terms in config/keywords.yaml, compiled once."""

    def __init__(self, keywords: KeywordsFile | None = None) -> None:
        keywords = keywords or load_keywords()
        self._terms: list[tuple[Kind, str, re.Pattern[str]]] = [
            ("direct_term", term, _term_pattern(term)) for term in keywords.direct_terms
        ] + [("code_word", term, _term_pattern(term)) for term in keywords.code_words]
        self._own = [(w, _term_pattern(w)) for w in keywords.own_computers.shows]
        self._not_own = [_term_pattern(w) for w in keywords.own_computers.unless]
        self._project = re.compile(keywords.project_code_name.pattern)
        self._stoplist = frozenset(
            word.lower() for word in keywords.project_code_name.project_stoplist
        )

    def find(self, text: str) -> list[Hit]:
        """Every hit in the text, in reading order."""
        hits: list[Hit] = []
        for kind, term, pattern in self._terms:
            hits.extend(
                Hit(kind, term, m.start(), m.end(), m.group(0)) for m in pattern.finditer(text)
            )
        for m in self._project.finditer(text):
            name = m.group(1)
            if name.lower() in self._stoplist:
                continue
            hits.append(Hit("project_code_name", f"Project {name}", m.start(), m.end(), m.group(0)))
        return sorted(hits, key=lambda h: (h.start, h.end, h.kind))

    def own_computers(self, text: str) -> str | None:
        """The word that shows the text is about a government's own computers, or None.

        None whenever the text also carries a word that shows land or a project. See
        `own_computers` in config/keywords.yaml.
        """
        if any(pattern.search(text) for pattern in self._not_own):
            return None
        return next((word for word, pattern in self._own if pattern.search(text)), None)


def strongest(hits: list[Hit]) -> Kind | None:
    """The strongest kind among the hits: a direct term, then a code name, then a code word."""
    kinds = {h.kind for h in hits}
    for kind in ("direct_term", "project_code_name", "code_word"):
        if kind in kinds:
            return kind  # type: ignore[return-value]
    return None


def snippet(text: str, start: int, end: int, margin: int = 100) -> str:
    """The words around a match, on one line, cut at word boundaries.

    An ellipsis marks each side that was cut. The match itself is never cut.
    """
    left = max(0, start - margin)
    right = min(len(text), end + margin)
    if left > 0:
        space = text.find(" ", left, start)
        left = space + 1 if space != -1 else left
    if right < len(text):
        space = text.rfind(" ", end, right)
        right = space if space != -1 else right
    body = " ".join(text[left:right].split())
    return ("… " if left > 0 else "") + body + (" …" if right < len(text) else "")
