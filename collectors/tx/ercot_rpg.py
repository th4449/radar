"""ERCOT Regional Planning Group meetings and the files posted for them.

The group reviews large transmission projects, which include lines built to serve large new
loads. The collector reads the group's index, the meetings near today and every file those
meetings list. See collectors/tx/ercot_meetings.py for how the pages are read.
"""

from __future__ import annotations

from collectors.tx import ercot_meetings
from collectors.tx.ercot_meetings import Committee, ErcotMeetings, Meeting, MeetingLink

INDEX = "https://www.ercot.com/committees/other/rpg"
RPG = Committee(index=INDEX, name="RPG")


def parse_index(body: bytes) -> list[MeetingLink]:
    return ercot_meetings.parse_index(body, RPG)


def parse_meeting(body: bytes, url: str = INDEX) -> Meeting:
    return ercot_meetings.parse_meeting(body, url)


class ErcotRpg(ErcotMeetings):
    source_id = "tx_ercot_rpg"
    committees = (RPG,)
