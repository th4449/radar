"""Meeting agendas of Michigan governments that publish through Legistar.

The collector is the one written for Texas, collectors/tx/legistar.py, pointed at Michigan's
agenda inventory. It reads the Legistar Web API and nothing else, and never fetches an agenda
file.

One Michigan government of 220 uses Legistar: Ann Arbor. Its boards share one calendar, so a
run takes every body's published agenda, not the council's alone. See
docs/sources/mi_agendas_legistar.md.
"""

from __future__ import annotations

from typing import ClassVar

from collectors.tx.legistar import LegistarAgendas


class MichiganLegistarAgendas(LegistarAgendas):
    """The list of meetings for each cleared Michigan government, then each new agenda."""

    source_id = "mi_agendas_legistar"
    state: ClassVar[str] = "MI"
