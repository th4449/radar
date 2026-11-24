"""Meeting agendas that Michigan governments post as files on their own websites.

The collector is the one written for Texas, collectors/tx/agenda_pages.py, pointed at
Michigan's agenda inventory. It reads each cleared page, finds the links to agenda files and
fetches the recent ones, four a page at most.

Where a list links no agenda file and gives each meeting a page of its own, the collector
follows the list to the recent meetings' pages, four at most, one more request a meeting. On
such a page it takes the agenda file the page links, or the page itself where the agenda is
written out on it. Texas' collector does not do this: it was built and tried on Michigan's
sites.

What it does not read, as it stands:

  an agenda file on another host than the government's own site, and
  a file whose address does not end in .pdf or .docx.

The run log names each. The governments this leaves out are listed in
docs/sources/mi_agendas_own_sites.md.
"""

from __future__ import annotations

from typing import ClassVar

from collectors.tx.agenda_pages import AgendaPages


class MichiganAgendaPages(AgendaPages):
    """Each cleared Michigan government's agenda page, then its recent agenda files."""

    source_id = "mi_agendas_own_sites"
    state: ClassVar[str] = "MI"
    follow_meeting_pages: ClassVar[bool] = True
