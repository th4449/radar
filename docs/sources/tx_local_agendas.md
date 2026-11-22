# Texas local agendas: the inventory

- Source id: `tx_local_agendas`
- Milestone: M8
- Inventory: `config/tx_agenda_inventory.csv`, 607 bodies of 334 governments
- Checks: `config/tx_agenda_checks.csv`, 410 independent reads. Rules: `pipeline/agenda_checks.py`
- Rules and loader: `pipeline/agenda_inventory.py`
- Researched: November 20, 2026. Checked a second time: November 21, 2026
- Result: **inventory done. No collector is written and no platform's terms have been read yet.** Every agenda source stays manual until its terms and robots rules are read.

## What the inventory is

One row for each public body in the 30 test counties: its government, the page where it posts agendas and the platform behind that page.

```bash
uv run python -m pipeline.agenda_inventory
```

prints the counts below from the file.

## Where the list of bodies came from

- **Counties.** The 30 in `config/counties_tx.yaml`. Each has a commissioners court.
- **Cities.** Every incorporated place in those counties, from the Census file `national_place_by_county2020.txt`, read November 20, 2026 (sha256 `9996494d…5d06ec6`). 304 places. They are in `config/tx_places.csv`. A place that lies in two of the 30 counties is listed once with both. Census designated places are left out: they have no government.
- **Development corporations.** The Comptroller's open dataset of Type A and Type B corporation reports, `d4dd-rd43` on data.texas.gov, marked public domain, last updated March 19, 2025. Its robots file sets a one second delay and does not bar the data addresses. Two requests were made. A corporation is in the inventory if it reported for fiscal 2022 or later and its city is one of the 304. That gave 178 names. The inventory has 187 development corporation rows. Research added some that cities list themselves, such as municipal development districts, and found that two of Maypearl's five listed names are the boards of two others.
- **Planning bodies.** Found by reading each city's site. There is no state list. **This part is not complete.** See below.

## How the platforms were found

Eleven research passes, one per group of counties, read each government's own website through search and page-reading tools. The brief they worked to:

- Official sites only.
- Never guess an address. Never work around a block, a captcha or a login. Submit no form.
- No names of people.
- A platform is named from an address, such as `/AgendaCenter` or `*.legistar.com`.
- An honest "not determined" beats a guess.

The results were then merged under one rule: **a row may claim only what its own addresses show.** `pipeline/agenda_inventory.py` holds the pattern for each platform and refuses a row that names a platform no address on it shows. The merge weakened 6 rows to "not determined" on that rule and marked 55 rows "inferred" because the page had been read through a search result and not opened.

## What it found

| Platform | Bodies | Governments | Counties |
|---|---:|---:|---:|
| Not determined | 183 | 39 | 21 |
| Files on the government's own site | 144 | 110 | 25 |
| CivicPlus Agenda Center | 86 | 51 | 16 |
| CivicClerk | 64 | 36 | 16 |
| Eleven smaller outside services | 32 | 26 | 15 |
| Legistar | 27 | 14 | 8 |
| No website | 23 | 22 | 14 |
| Municode Meetings | 21 | 13 | 11 |
| Swagit | 9 | 7 | 3 |
| CivicWeb | 7 | 6 | 6 |
| County association site | 5 | 5 | 5 |
| Granicus | 5 | 4 | 4 |
| Other | 1 | 1 | 1 |

"Governments" counts the commissioners court or city council row. The smaller services each have a name in the inventory since November 22, 2026: Google Drive 11 governments, HeyGov 4, TownCloud 3, eCode360 2, and one each on Diligent Community, Documents On Demand, Municipal Impact, JustMeetings, Dropbox and the Laserfiche portal. BoardBook has none left. "Other" is Matagorda County, whose agenda page shows no agenda.

- **Four platforms hold 114 of the 334 governments:** CivicPlus Agenda Center, CivicClerk, Legistar and Municode Meetings.
- **The 30 commissioners courts:** CivicPlus Agenda Center 10, county association site 5, CivicClerk 3, own site 3, Legistar 2, Documents On Demand 1, other 1, CivicWeb 1, Granicus 1, not determined 3 (Callahan, Hopkins, San Saba).
- **111 governments post files on their own sites.** Each site is laid out its own way. The first count was 114. A browser read on November 22, 2026 found four of them post elsewhere: Cibolo, Slaton, Reno and Runaway Bay. The same day Milam County was found to post on its own site as well as on BoardBook. For one of the 111, New Deal, the row is not the council's.
- **22 governments have no website.** These are small towns. Some have a Facebook page only.
- **The five large counties are not the hard part.** Dallas has 22 of 32 governments on the four platforms and Harris 18 of 35. Nine rural counties have none: Hill, Austin, Archer, Hood, Falls, Callahan, Carson, Hopkins and San Saba.
- **Several cities run two systems at once,** an older Agenda Center and a newer CivicClerk portal. The notes on those rows name both.

## How accuracy is kept

One read of a website can be wrong. So a row is trusted only when a second, independent read of the same page agrees with it.

1. **The address rule.** A row may name only the platform its own addresses show. The loader refuses any other row.
2. **A second read of every page.** `config/tx_agenda_checks.csv` records it. The second reader is not told what the inventory says and never names a platform. It copies what is on the page: the agenda addresses, the newest agenda's date and the bodies listed. `pipeline/agenda_checks.py` names the platform from those addresses and compares.
3. **A verdict for every row.** Confirmed means the two reads agree on the platform, the body was listed and the newest agenda is under 400 days old. Anything less has its own verdict and its own reason.
4. **A gate.** `collectable()` is true only for a confirmed row. A test holds it. No agenda collector takes any other row.
5. **A check goes stale.** After 180 days a row is no longer confirmed and must be read again. Governments change platforms.
6. **A list for a person.** `uv run python -m pipeline.agenda_checks --csv` writes every row that is not settled, with the reason, commissioners courts first. A person opens the page and adds a line to the checks file with `by` set to `hand`. A person's check outranks every other.

```bash
uv run python -m pipeline.agenda_checks
```

prints the counts by verdict.

## The wider check, November 21, 2026

Ten research passes read 320 agenda pages a second time. They also searched again for a site for each of the 22 towns recorded as having none, and looked again for each of the 60 governments whose agendas the first read could not place. That is 402 checks.

**How the first read held up.** On 316 rows that named a platform, a check could be set beside the first read. **311 agreed on the platform. 5 did not.**

- Grand Prairie's planning commission was wrong. The first read carried the council's platform to it. The page is an archive that stops in 2021. The row is corrected.
- Palmer and Hilshire Village each run two systems, and the two reads saw different ones.
- Taylor County's second read copied only an older address. It is not a real disagreement and needs a look.
- Industry's agenda address now answers "page not found".

**No website:** all 22 held. A second search found no official site for any of them.

**Not determined:** the second read found the agendas for 21 of the 60 governments. Those rows are filled in. They rest on one read again, so they are not confirmed.

**What each row has earned**

| Verdict | Bodies | Governments |
|---|---:|---:|
| Confirmed | 267 | 182 |
| Both reads found no website | 23 | 22 |
| Undetermined: no agenda page known | 167 | 32 |
| Unreadable: the page fills itself in by script | 47 | 33 |
| Platform agrees, this body not seen listed | 29 | 10 |
| Not shown: the page listed no agendas | 30 | 20 |
| Unchecked: found by one read only | 20 | 20 |
| Not current: newest agenda old or undated | 15 | 11 |
| Contradicted | 9 | 4 |

**290 bodies are settled. 317 need a person.** Of those, 126 are development corporations with no agenda page known. That is research, not checking.

**By government, 204 of 334 are settled and 130 need one hand read:**

| Group | Governments | Settled | Need a person |
|---|---:|---:|---:|
| CivicPlus Agenda Center | 51 | 34 | 17 |
| CivicClerk, Legistar, Municode Meetings | 63 | 49 | 14 |
| County association sites, Swagit, CivicWeb, Granicus | 22 | 13 | 9 |
| Files on the government's own site | 114 | 75 | 39 |
| Other outside platform | 23 | 11 | 12 |
| Not determined | 39 | 0 | 39 |
| No website | 22 | 22 | 0 |

17 of the 30 commissioners courts are confirmed.

**Why so many are unreadable.** The page-reading tool cannot run a page's scripts. A list that fills itself in comes back empty. I opened 14 of those pages in a real browser. 4 showed a current list and are confirmed. 4 showed a real problem: a missing page, an Agenda Center with no files in it, a list embedded from another host and a page that only points elsewhere. On 6 my reading script could not tell, and they stay on the list. A person with a browser settles each of these in about a minute.

## What is not verified

- **317 rows are not settled.** The list is the output of the command above.
- A confirmed row means two reads agreed. Both reads were research passes, not people. I opened 27 pages myself across both days.
- The newest agenda's date is what the second reader saw on the page. On a page that lists several bodies it may belong to another body.
- **Planning bodies are incomplete.** 86 cities have a planning row. For 88 cities the first read did not look or did not say. A city with no row may still have a planning commission.
- A match between a state-listed corporation and a city is by city name.
- **No platform's terms of use or robots rules have been read.** A confirmed row says where the agendas are. It does not say they may be collected.

## What comes next

**The owner approved building the collectors by platform. The first reading of the platforms' own rules then stopped the first batch.** The full account is in [tx_agenda_platform_terms.md](tx_agenda_platform_terms.md).

- **CivicPlus' terms restrict the radar's use.** They cover the Agenda Center, CivicClerk and Municode Meetings: 100 governments.
- **Granicus pages, Swagit and CivicWeb are closed by their robots files:** 17 governments.
- **Legistar is cleared and has a collector.** It reads 9 of the 14 governments on it. See [tx_agendas_legistar.md](tx_agendas_legistar.md).
- **The county association sites are cleared and read by the own-sites collector:** 5 commissioners courts. Three keep their agendas in a calendar, which is read through its feed.
- **The eleven smaller outside services were read on November 22, 2026.** Seven are closed, four by a robots file and three by terms: 9 governments. Nothing was found against Google Drive, HeyGov, JustMeetings or the Laserfiche portal: 17 governments. **The owner cleared HeyGov that day.** Two of its four cities are read by the own-sites collector. The other two draw their lists from HeyGov's API, whose robots file bars every agent. Google Drive, JustMeetings and the Laserfiche portal are not cleared. That takes the owner's word.
- **Own sites are cleared one site at a time and have a collector.** Of 111 governments, 99 have a confirmed row. 52 are read. See [tx_agendas_own_sites.md](tx_agendas_own_sites.md).

`collectable()` needs three things: a row an independent check confirmed, a platform marked `cleared` in `config/tx_agenda_platforms.csv`, and the government's own terms read with nothing against it in `config/tx_agenda_site_terms.csv`. A test pins each platform's standing.
