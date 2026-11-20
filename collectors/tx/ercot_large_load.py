"""ERCOT's reports on large loads waiting to connect to the grid.

ERCOT posts them for two committees:

- the Large Load Working Group. Every file its meetings list is fetched.
- the Technical Advisory Committee, which gets a large load status update at most meetings.
  Its meetings list many files on other subjects. Only files with "large load" in the title
  are fetched.

These reports give totals by year and zone. They do not name sites. They are context for the
signals, not signals themselves. See collectors/tx/ercot_meetings.py for how the pages are read.
"""

from __future__ import annotations

import re

from collectors.tx.ercot_meetings import Committee, ErcotMeetings

LLWG_INDEX = "https://www.ercot.com/committees/tac/llwg"
TAC_INDEX = "https://www.ercot.com/committees/tac"

LLWG = Committee(index=LLWG_INDEX, name="LLWG")
TAC = Committee(index=TAC_INDEX, name="TAC", files=re.compile(r"large[ _-]*load", re.IGNORECASE))


class ErcotLargeLoad(ErcotMeetings):
    source_id = "tx_ercot_large_load"
    committees = (LLWG, TAC)
    # The planned cadence is monthly, so a run looks further back than the weekly feeds do.
    back_days = 45
