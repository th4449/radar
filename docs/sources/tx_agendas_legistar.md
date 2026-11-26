# Texas agendas on Legistar

- Source id: `tx_agendas_legistar`
- Interface: the Legistar Web API, https://webapi.legistar.com/
- Vendor: Granicus
- Checked: November 21, 2026
- Result: **allowed, through the published API only, for 9 of 14 governments.** Five are held out.
- Collector: `collectors/tx/legistar.py`
- Fixtures: `tests/fixtures/tx_agendas_legistar/`, three real answers, one of them trimmed
- Workflow: `.github/workflows/collect-tx-agendas-legistar.yml`, started by hand only

The owner said on November 21, 2026 to go on with the build while CivicPlus considers the request for consent. Legistar was the next platform. Its rules were read first.

## What was verified

**The API is published for programs.** Granicus' page at webapi.legistar.com says the API exposes Legistar data to the web over HTTPS. Its examples page shows how to list meetings and page through results. Granicus' support article of September 29, 2025 documents the same calls. Both say:

- A read returns only items marked public.
- Paging and filtering reduce the load on the server.
- Some governments require a token. That is each government's policy.

**Neither page states terms of use or a rate limit.**

**Granicus' website terms,** https://granicus.com/trust-center/terms-of-use/, dated July 20, 2026, read in full. They speak of "this website", meaning granicus.com. They reserve copyright in its material. They say nothing about automated access and do not name Legistar.

**Robots files,** one identified request each:

| Host | Answer |
|---|---|
| `webapi.legistar.com` | 404. No rules |
| each of the 14 governments' `*.legistar.com` hosts | 404. No rules |
| `legistar.granicus.com`, `legistar2.granicus.com` | **Bars every agent from every path** |

The agenda PDFs sit on the hosts that bar robots, and on hosts like them. **So the collector never fetches an agenda file.** It reads the agenda's items through the API, which is where the vendor offers them.

**No token is needed.** All 14 governments answered a request for their three newest meetings without one.

## Which governments are read

The agenda inventory decides, not the collector. A government is read only when its row is confirmed by an independent check, the platform is cleared and its own terms were read with nothing against it.

**Read: 9.** Carrollton, Coppell, Dallas, Deer Park, Farmers Branch, Harris County, Lewisville, Pflugerville and Round Rock.

| Government | Its own terms |
|---|---|
| Carrollton, Dallas | A disclaimer bars commercial use without written permission. Nothing on automated access. The radar is not commercial |
| Coppell, Pflugerville | A copyright line. Nothing on automated access |
| Farmers Branch | A copyright line, and a privacy page that says its content is public information that may be copied |
| Lewisville | Bars copying site content, and says public documents such as agendas may be copied and distributed, not modified |
| Harris County | A privacy page says servers watch for attempts to upload or change information. Nothing on reading |
| Deer Park, Round Rock | No terms, copyright or privacy page linked from the home page |

**Held out: 5.**

| Government | Why |
|---|---|
| League City | Its terms bar reproducing or distributing site material without the city's prior written consent |
| Lubbock County | Its terms limit downloads to personal, noncommercial use and bar reuse and derivative works without written permission |
| Fort Worth | Its website policies bar copying without prior written consent. Its newest meeting on Legistar is from June 2026, so it may have moved |
| University Park | The city's site did not load for the reader. Its terms are unread |
| San Antonio | Its newest meeting on Legistar is from 2021. It has moved, and its row is not confirmed |

None of the three held for their terms says anything about automated access. They limit reuse. The radar keeps a copy of what it reads and publishes a short notice with a link. Whether that is the reuse those terms mean is the owner's call, so they wait.

## What the collector does

For each government, one run makes:

1. **One request** for the list of meetings from 14 days ago onward.
2. **One request for each meeting** whose agenda is published and is new or changed since the last run.

- Requests go through the shared fetcher: one every 5 seconds to the API's host, with the radar's user agent and contact address.
- At most 40 meetings for one government in one run. The rest wait for the next run and the run log says how many.
- A meeting that has not changed is not asked for again.
- A refusal ends the run. Nothing is retried by another route.

**What is stored** for a meeting: its body, date, time, place and status, the address of its public page and each item's number, file number, type, title and note. Who moved, seconded or voted is dropped. So is the address of the agenda file.

**The source is marked `personal_rows`.** An agenda names staff, appointees and applicants. Its stored text is open to administrators and not to reviewers, and none of it is ever sent to the model.

## What becomes a signal

`legistar_agenda` in `pipeline/signals.py` reads each item's title and note. An item that uses a term in `config/keywords.yaml` becomes one `agenda_keyword` signal, the lowest weight in the scoring.

- **The summary never quotes the item.** It names the body, the meeting, the item's number and the words that matched. An item can name a private person.
- The words around the match are kept beside the signal for the reviewer.
- The reviewer opens the meeting's own page, whose address is kept with the signal.

**Many matches are not about a development.** A county buys "data center" services for its own computers. A board appointment names a "reinvestment zone". The radar cannot tell these apart. A reviewer can.

**Changed on November 23, 2026, after the backtest and with the owner's approval.**

- An item that says "data center" is held to its government and meeting, so it sits on a site, and at the review threshold of 3 it reaches a reviewer by itself. Before, an agenda signal sat on no site. In four years of stored agendas this sends a reviewer 54 such sites that fit no known project, many of them a government's own computer rooms.
- An item that uses a code word alone still opens no site.
- **An item about the government's own computers is set aside.** The words "data center" make no signal where the item also says, for example, co-location, network services or information technology, and says nothing of land or a project. See `own_computers` in `config/keywords.yaml`. In four years of stored agendas this takes out 26 of the 28 sites the owner rejected as a government's own computers, and none the owner confirmed.
- "Project" and a code name is a reason only where the item itself speaks of economic development negotiations or cites Government Code 551.087. In the backtest 399 signals rested on a code name and three were tied to a known project. **An item whose heading sits in an earlier item is missed.**

## Verified live

On November 21, 2026:

- The three newest meetings of each of the 14 governments, one request each. All answered.
- A search of four governments' records for the words "data center". Harris County's commissioners court took up data center development in the county on October 15, 2026. Dallas has had two briefings on data centers this year. Pflugerville's development corporation held a hearing in 2022 on an agreement with a data center company. Round Rock's matches were its own equipment purchases.
- Harris County's meeting of October 15, 2026: 1,740 items in one answer of 2 MB.
- **A run of the collector itself** on the nine governments, capped at five meetings each for a first look. 41 requests, no errors and no refusal. It read 32 meetings holding 1,207 agenda items. Nothing was written to a database.
- **The first real run,** November 26, 2026, started by hand on GitHub on the owner's word: 70 requests, no errors and no refusal, in 5 minutes 50 seconds. It stored 9 lists of meetings and 61 meetings holding 1,461 agenda items, dated November 12 to December 9, 2026. No government reached the cap of 40. All 70 are extracts and are marked restricted. Run: https://github.com/th4449/radar/actions/runs/45892001196.
- **The signal step on those 32 meetings: 7 signals from 1,207 items.** Four items name a reinvestment zone, two a light industrial zoning and one a data center.
  - One is the kind the radar exists for: a city council item designating a reinvestment zone for a named company.
  - The data center item is Harris County buying a service for its own computers.
  - The first pass gave 15 signals. Eight were "Project" followed by an ordinary word, such as a funding line. Those words are now on the list of words that are not code names.

## What was not verified

- **Any stated limit on requests.** None is published. The fetcher's pace is one request every 5 seconds.
- Whether Granicus' unwritten expectations for the API differ from its published pages. The support article is written for its customers.
- The agenda note field in practice. Most items carry a title and no note.
- How a government that later requires a token answers. The run would end as blocked.
- A run from GitHub's servers.
- The five governments held out.

## For the owner

- **Three governments wait on your word:** League City, Lubbock County and Fort Worth. Their terms ask for written consent to reuse their content. Lubbock County is one of the 30 commissioners courts.
- University Park needs its site read again.
- Nothing runs on a schedule. The workflow is started by hand.
