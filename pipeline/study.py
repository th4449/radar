"""Which companies on record have the same name as a payer in the QPQ Tracker's study.

See BUILD_PLAN.md milestone M12. The study of who paid for the data centers lists the payers
it counts. The radar keeps a copy of that page (collectors/us/qpq_data_center_payers.py) and
this module compares names.

A match is by name and nothing more.

  same_name                    the record gives the payer's name, or a listed other name, as
                               it stands: "Oncor", "DTE Electric Company".
  same_name_legal_form_aside   the same name once the record's legal form is set aside:
                               "Georgia Power Company" meets the listed "Georgia Power".

A name listed with its own legal form, such as "DTE Electric Company", is one company's name.
It meets a record only as written, so "DTE Electric LLC" does not meet it.

A name never matches a longer name that merely contains it, so a project filed under a new
company's name does not meet its parent. A match says the name is in the study. It says nothing
about a site and it is never proof that two names are one company.

The other names a payer goes by, and the names too ordinary to match loosely, are kept by hand
in config/study_payers.yaml.

The payers and the matches in the database are rebuilt from the newest stored copy of the page
on every processing run. They hold no decision a person made, so nothing is lost.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import psycopg

from collectors.base import ArchiveStore, LayoutChanged
from collectors.us.qpq_data_center_payers import Payer, parse
from pipeline.config import StudyPayersFile, load_study_payers
from pipeline.entities import canonical_name, match_key

SOURCE_ID = "us_qpq_data_center_payers"

SAME_NAME = "same_name"
LEGAL_FORM_ASIDE = "same_name_legal_form_aside"


@dataclass(frozen=True)
class Match:
    payer: Payer
    basis: str
    matched_name: str  # the payer's label or the listed other name that the record's name met


class PayerNames:
    """The names a company on record can meet, each leading to one payer."""

    def __init__(self, payers: Iterable[Payer], names: StudyPayersFile | None = None) -> None:
        names = names or load_study_payers()
        payers = list(payers)
        by_label = {p.name: p for p in payers}
        whole_only = {canonical_name(n) for n in names.whole_name_only}

        self._exact: dict[str, tuple[Payer, str]] = {}
        self._loose: dict[str, tuple[Payer, str]] = {}
        # A payer the file names that the study no longer lists. Reported, never an error: the
        # study may drop a payer between two runs.
        self.unlisted: list[str] = sorted(
            {entry.payer for entry in names.other_names if entry.payer not in by_label}
        )

        pairs = [(p, p.name) for p in payers]
        pairs += [
            (by_label[entry.payer], name)
            for entry in names.other_names
            if entry.payer in by_label
            for name in entry.names
        ]
        for payer, name in pairs:
            exact = canonical_name(name)
            self._claim(self._exact, exact, payer, name)
            # A name listed with its legal form is one company's own name. It meets a record
            # only as written: "Switch, Ltd." must not let "Switch LLC" in.
            if exact == match_key(name) and exact not in whole_only:
                self._claim(self._loose, exact, payer, name)

    @staticmethod
    def _claim(held: dict[str, tuple[Payer, str]], key: str, payer: Payer, name: str) -> None:
        if key in held and held[key][0] != payer:
            raise ValueError(
                f"{name!r} would lead to two payers: {held[key][0].name!r} and {payer.name!r}"
            )
        held.setdefault(key, (payer, name))

    def match(self, name: str) -> Match | None:
        """The payer whose name this is, or None. `name` is a company's name as a record gave it."""
        exact = canonical_name(name)
        if exact in self._exact:
            payer, met = self._exact[exact]
            return Match(payer, SAME_NAME, met)
        key = match_key(name)
        if key in self._loose:
            payer, met = self._loose[key]
            return Match(payer, LEGAL_FORM_ASIDE, met)
        return None


def update(
    conn: psycopg.Connection, store: ArchiveStore, names: StudyPayersFile | None = None
) -> dict:
    """Rebuild the payers and the matches from the newest stored copy of the study's page.

    Returns counts for the run log. When no copy is stored, or the newest copy cannot be read,
    the tables are left as they are and the reason is returned under "error" or "note".
    """
    row = conn.execute(
        """select d.id, d.storage_path, d.retrieved_at
           from public.documents d join public.sources s on s.id = d.source_id
           where s.slug = %s
           order by d.retrieved_at desc, d.id desc
           limit 1""",
        [SOURCE_ID],
    ).fetchone()
    if row is None:
        return {"note": "No copy of the study's list of payers is stored."}
    document_id, storage_path, retrieved_at = row
    try:
        payers = parse(store.get(storage_path))
        known = PayerNames(payers, names)
    except (LayoutChanged, OSError, ValueError) as exc:
        return {"error": f"document {document_id}: {exc}"}

    conn.execute("delete from public.study_payers")  # its matches go with it
    ids: dict[str, int] = {}
    for payer in payers:
        ids[payer.name] = conn.execute(
            """insert into public.study_payers (document_id, name, payer_class, url, states)
               values (%s, %s, %s, %s, %s) returning id""",
            [document_id, payer.name, payer.payer_class, payer.url, list(payer.states)],
        ).fetchone()[0]

    matched = 0
    for entity_id, name in conn.execute("select id, name from public.entities").fetchall():
        found = known.match(name)
        if found is None:
            continue
        conn.execute(
            """insert into public.entity_study_payers (entity_id, payer_id, basis, matched_name)
               values (%s, %s, %s, %s)""",
            [entity_id, ids[found.payer.name], found.basis, found.matched_name],
        )
        matched += 1
    out = {
        "document_id": document_id,
        "read_on": retrieved_at.date().isoformat(),
        "payers": len(payers),
        "companies_matched": matched,
    }
    if known.unlisted:
        out["other_names_for_a_payer_not_on_the_list"] = known.unlisted
    return out
