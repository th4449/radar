# Michigan agendas on Legistar

- Source id: `mi_agendas_legistar`
- Interface: the Legistar Web API, https://webapi.legistar.com/
- Vendor: Granicus
- Checked: November 23, 2026, in part
- Result: **one government, Ann Arbor. Not read by any job.** The source is marked `manual`.
- Collector: none yet. Texas' is `collectors/tx/legistar.py`

Of 220 governments in the six counties, one posts its agendas on Legistar: Ann Arbor. Its council, planning commission, downtown authority and finance authority share one calendar at `a2gov.legistar.com`.

## What was verified

- **The inventory rows are confirmed.** An independent second read of the calendar page on November 23, 2026 saw dated agendas for the bodies.
- **Robots:** `a2gov.legistar.com` answered 404 to the radar's reader on November 23, 2026. No rules. `www.a2gov.org` has a robots file that bars six system folders and nothing else.
- **The city's own terms:** its policies page says information on the site "is considered public information and may be distributed or copied", but for logos and for material marked with a copyright. Nothing on automated access. Read in full by the radar's reader.
- **Granicus' terms and the Legistar Web API** were read for Texas on November 21, 2026. See [tx_agendas_legistar.md](tx_agendas_legistar.md). The API is published for programs and a read returns only public items.

## Not verified

- **Whether Ann Arbor's Legistar answers the API without a token.** Some governments require one. No request has been made to the API for `a2gov`.
- The calendar page came back cut off before its foot, so any terms linked there were not seen.
- The Texas collector never fetches an agenda file, because the hosts that store them bar robots. Where Ann Arbor's files sit was not checked.

## Before a collector reads it

1. The owner says whether the clearing of Legistar, given for Texas on November 21, 2026, holds for Michigan.
2. One identified request to the API for Ann Arbor's three newest meetings, saved as a fixture.
3. A Michigan collector as a thin subclass of the Texas one, with tests on the fixture.
4. The source's method changes from `manual` only on the owner's word.
