# Michigan agendas on Legistar

- Source id: `mi_agendas_legistar`
- Interface: the Legistar Web API, https://webapi.legistar.com/
- Vendor: Granicus
- Checked: November 23, 2026
- Result: **one government, Ann Arbor. A collector is written. Not read by any job.** The source is marked `manual`.
- Collector: `collectors/mi/legistar.py`, which is Texas' `collectors/tx/legistar.py` pointed at Michigan's inventory
- Tests: `tests/test_mi_agendas_legistar.py`, on two saved answers

Of 220 governments in the six counties, one posts its agendas on Legistar: Ann Arbor. Its council, planning commission, downtown authority and finance authority share one calendar at `a2gov.legistar.com`.

## What was verified

- **The inventory rows are confirmed.** An independent second read of the calendar page on November 23, 2026 saw dated agendas for the bodies.
- **Robots:** `a2gov.legistar.com` answered 404 to the radar's reader on November 23, 2026. No rules. `www.a2gov.org` has a robots file that bars six system folders and nothing else.
- **The city's own terms:** its policies page says information on the site "is considered public information and may be distributed or copied", but for logos and for material marked with a copyright. Nothing on automated access. Read in full by the radar's reader.
- **Granicus' terms and the Legistar Web API** were read for Texas on November 21, 2026. See [tx_agendas_legistar.md](tx_agendas_legistar.md). The API is published for programs and a read returns only public items.

- **The owner said on November 23, 2026 that the clearing of Legistar given for Texas holds for Michigan.**
- **The API answers for Ann Arbor without a token.** Two identified requests on November 23, 2026: the list of meetings from November 9 on, and one council meeting. The list held eight meetings, six with a published agenda. Both answers are saved as fixtures.

## What a run would take

- One request for the list of meetings from 14 days back, then one for each meeting whose agenda is published and is new or changed.
- **Every body on the calendar, not the four in the inventory.** The list held the council, three council committees, the housing commission, two retirement boards and a fund committee. Texas' collector reads a government's whole calendar the same way.
- Each item's number, file number, type, title and note. Who moved, seconded or voted is dropped. No agenda file is fetched.
- **An agenda can name people who signed up to speak.** The council meeting of November 16 listed two speakers by name as agenda items. A stored agenda would hold such names. The source is marked as holding personal rows, and the fixture leaves those two items out.

## Not verified

- The calendar page came back cut off before its foot, so any terms linked there were not seen.
- Where Ann Arbor's agenda files sit was read from the API's answer: `a2gov.legistar1.com`. Its robots file was not read, and the collector never asks that host.
- **One run by hand, November 23, 2026, on the owner's word, nothing stored.** Seven requests: the list and the six published agendas. All answered. 127 agenda items, no draft signal.
- The code-name signal rule is untried on Michigan agendas.

## Before a job reads it

1. The owner says to run it.
2. The source's method changes from `manual` to `http`, the collector goes on the list in `collectors/run.py` and a workflow file is added. A test holds all three together.
