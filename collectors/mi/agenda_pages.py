"""Meeting agendas that Michigan governments post as files on their own websites.

The collector is the one written for Texas, collectors/tx/agenda_pages.py, pointed at
Michigan's agenda inventory. It reads each cleared page, finds the links to agenda files and
fetches the recent ones, four a page at most.

What it does not read, as it stands:

  a page whose list leads to a page for each meeting and not to a file, and
  a file whose address does not end in .pdf or .docx.

Such a page is named in the run log as one with no agenda links. The governments this leaves
out are listed in docs/sources/mi_agendas_own_sites.md.
"""

from __future__ import annotations

from typing import ClassVar

from collectors.tx.agenda_pages import AgendaPages


class MichiganAgendaPages(AgendaPages):
    """Each cleared Michigan government's agenda page, then its recent agenda files."""

    source_id = "mi_agendas_own_sites"
    state: ClassVar[str] = "MI"
