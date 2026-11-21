# Texas local agendas: the inventory

- Source id: `tx_local_agendas`
- Milestone: M8
- Inventory: `config/tx_agenda_inventory.csv`, 607 bodies of 334 governments
- Rules and loader: `pipeline/agenda_inventory.py`
- Researched: November 20, 2026
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
| Not determined | 203 | 60 | 24 |
| Files on the government's own site | 134 | 99 | 25 |
| CivicPlus Agenda Center | 86 | 51 | 16 |
| CivicClerk | 63 | 35 | 16 |
| Legistar | 27 | 14 | 8 |
| No website | 23 | 22 | 14 |
| Other outside platform | 23 | 18 | 14 |
| Municode Meetings | 22 | 13 | 11 |
| Swagit | 9 | 7 | 3 |
| CivicWeb | 7 | 6 | 6 |
| County association site | 5 | 5 | 5 |
| Granicus | 5 | 4 | 4 |

"Governments" counts the commissioners court or city council row. "Other" is HeyGov, TownCloud, Google Drive folders, Diligent Community, BoardBook, Laserfiche, Documents On Demand, Dropbox and ezTask.

- **Four platforms hold 113 of the 334 governments** and 198 of the 607 bodies: CivicPlus Agenda Center, CivicClerk, Legistar and Municode Meetings.
- **The 30 commissioners courts:** CivicPlus Agenda Center 10, county association site 5, CivicClerk 3, other platforms 3, Legistar 2, own site 2, CivicWeb 1, Granicus 1, not determined 3 (Callahan, Hopkins, San Saba).
- **99 governments post files on their own sites.** Each site is laid out its own way.
- **22 governments have no website.** These are small towns. Some have a Facebook page only.
- **The five large counties are not the hard part.** Dallas has 22 of 32 governments on the four platforms and Harris 18 of 35. Nine rural counties have none: Hill, Austin, Archer, Hood, Falls, Callahan, Carson, Hopkins and San Saba.
- **Several cities run two systems at once,** an older Agenda Center and a newer CivicClerk portal. The notes on those rows name both.

## Checked by hand

I opened 13 rows myself on November 20, 2026, drawn at random by platform:

- **Confirmed, with a current agenda on the page:** Pasadena and Eustace (Agenda Center), West Lake Hills (CivicClerk), Lubbock County (Legistar), Hutchins and Boyd (Municode Meetings), Caney City (own site), Carson County (county association site), Granbury (Granicus), Ennis (CivicWeb), Murchison (TownCloud).
- **Could not be read:** Waxahachie's agenda page shows an embedded player and no links. Its row is "inferred" and says so.
- **No website:** a search for Kirvin found a directory entry and no official site, as the row says.
- **One row was wrong, and the fault was the merge's.** Southside Place has an Agenda Center page, and it is empty. Its files are in the city's Document Center. The row is now "not determined" with that note.
- Hutchins' page showed the same agenda at `meetings.municode.com` and at `mccmeetings.blob.core.usgovcloudapi.net`. That second host is where Municode Meetings keeps the files, and the rules now recognize it.

## What is not verified

- **594 of the 607 rows were not opened by me.** They rest on the research passes and on the address rule.
- **171 rows are "inferred".** The platform was seen for the government, or the page was read through a search result. The body's own list was not opened.
- **Planning bodies are incomplete.** 86 cities have a planning row. For 130 cities the research saw no sign of one. For 88 it did not look or did not say. A city with no row may still have a planning commission.
- **129 of the 187 development corporations have no agenda location.** Most post nothing of their own, or post on a page that was not opened.
- **60 governments are "not determined".** Most have a site whose agenda list loads by script, or a page with no readable links.
- **"No website" rests on one or two searches each.**
- Whether an agenda list is current. Some rows note a list that stops in an earlier year.
- A match between a state-listed corporation and a city is by city name.
- **No platform's terms of use or robots rules have been read.** Nothing here says any of these may be collected.

## What comes next, and a change to the plan

The plan calls for three batches of ten counties. The inventory says agendas are sorted by platform, not by county: one collector for one platform reaches every county that uses it. I propose batches by platform:

1. **CivicPlus Agenda Center.** 51 governments in 16 counties, 10 commissioners courts among them.
2. **CivicClerk, Legistar and Municode Meetings.** 62 governments, 5 commissioners courts among them.
3. **County association sites, then Swagit, CivicWeb and Granicus.** 22 governments, 7 commissioners courts among them.

That reaches 135 governments and 22 of the 30 commissioners courts. It leaves:

- 99 governments with files on their own sites. One general collector could read a page of file links, with one configured entry per site.
- 18 on small outside platforms, 60 not determined and 22 with no website. These are for a reviewer to read by hand, or for a second research pass.

**Before any collector:** each platform's terms and robots rules are read and recorded, and so are those of each government's site the collector would touch. An Agenda Center page sits on the city's own domain, so the city's terms apply as well as the platform's. A site that restricts automated access is marked manual.

This order is a proposal. It changes the plan's batches and needs the owner's approval.
