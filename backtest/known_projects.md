# Known projects: how the list is made

`known_projects_tx.csv` is the backtest's list of known data center projects in the 30 Texas test counties. It was built from news reports and public records only. On November 23, 2026 it was checked against FracTracker Alliance's dataset: see the section below. `backtest/projects.py` loads it and refuses a row that breaks a rule.

It holds **128 projects in 25 counties**. 126 were researched on November 22, 2026. Two were added on November 23 from the check against FracTracker's dataset.

**The date a project became public is its `news_date`:** the first news report or company announcement. The owner settled that on November 22, 2026. A government record is a signal, never the public date. **A local blog counts as a first report.** The owner settled that on November 23, 2026. One Tom Green County row rests on one.

**Nothing here is a finding about a company or a place.** A row says what a dated source says. A date is the earliest found, not the earliest that exists.

## How it was made

- **One research pass per county,** two for Dallas County. Each searched news sites, trade press, company releases and government pages for the earliest dated report that calls each project a data center, and for the earliest dated government record.
- The first three counties were a trial: Hood, Hill and Milam, 23 projects. The owner then said to carry on with the other 27 the same way.
- **Every pass carried the collectors' rules in its brief:** a plain connection only, robots files honored, a list of barred hosts, stop at a refusal, no reprint of a closed paper, no private individuals.
- **A second read by a separate pass** then opened the cited pages again and reported what each page itself shows: the date, whether it calls the project a data center and whether it names the place. It ran no searches.
- **One row per site.** The backtest matches a signal to a project by place and company, and gives a signal that fits two projects to neither. A later phase or a second developer on the same site is in the row's notes.
- Bitcoin mines are listed only where a source calls them a data center. The `crypto` column marks them.
- In Dallas, Bexar, Travis and Harris counties only new builds, campuses and expansions first made public since January 1, 2023 are listed. About 130 older operating buildings were seen there and left out.
- No private individual is named. Companies, their LLCs and officials acting in office are.

## The columns that carry the dates

| Column | Meaning |
|---|---|
| `record_date` | The earliest dated record found that calls the project a data center. Where no government record was found it is the earliest report of any kind |
| `record_kind` | What that is. `county_meeting`, `county_hearing` and `city_meeting` mean a government action known only from a news report. `county_minutes`, `city_minutes`, `county_agenda`, `county_notice`, `zoning_case` and `state_filing` mean the address is the record itself |
| `news_date` | The earliest news report or company announcement found. The public date |
| `record_read`, `news_read` | How far the cited page was checked. See below |
| `confidence` | `high` both dates read and nothing older found. `medium` one read. `low` otherwise, and whenever the second read found a gap |

How far a page was checked:

- `second_read`: opened twice, the second time by a check that did not do the research. The date held, the page calls the project a data center and it names the place.
- `first_read`: opened by the research pass only, or the second read found a gap. The gap is in the notes after the words SECOND READ.
- `not_opened`: known from a headline, a search excerpt or another source.
- `set_aside`: read against a block, or on a site since treated as closed. The date is removed and a person needs to date the row.
- `none_found`.

## What it holds

| County | Projects | County | Projects |
|---|---|---|---|
| Dallas | 28 | Travis | 3 |
| Bexar | 16 | Austin | 2 |
| Ellis | 10 | Carson | 2 |
| Hood | 10 | Henderson | 2 |
| Harris | 9 | Somervell | 2 |
| Milam | 7 | Taylor | 2 |
| Hill | 6 | Archer | 1 |
| Lubbock | 5 | Bosque | 1 |
| Potter | 4 | Callahan | 1 |
| Tom Green | 4 | Freestone | 1 |
| Bowie | 3 | Hopkins | 1 |
| Johnson | 4 | Parker | 1 |
| Matagorda | 3 | | |

**No known project was found in five counties:** Burnet, Erath, Falls, San Saba and Wise. In each, the county's agendas or the local papers were closed to the pass, so "none found" is weak.

- **79 of the 128 have a public date.** 73 of those fall in 2023 or later, inside the years the radar's records can cover.
- **49 have none.** No news report was found, or the only one sits on a site closed to the reader.
- 75 have a dated government record. 45 of those were read on the page.
- **34 records are state building registrations** at the Texas Department of Licensing and Regulation. No other kind is as common. The plan does not list that source.

## What it shows about records and news, and what it does not

For 18 projects both a government record and the first report were read on the page.

- In **9** the record came first, by 5 to 918 days.
- In **9** the record came after the first report, by 3 to 416 days.
- The median is a record one day ahead.

**This is not a measured lead time, and it is not the backtest.**

- A news date is the earliest report found. Several local papers bar the reader, and an older story there would shorten or erase a lead.
- A state registration is filed when a building is designed, which can be long after a campus is announced. Six of the nine late records are registrations.
- The two longest leads are doubtful. The pass that found the 918-day one says the registration may not be the same work as the announcement.
- It counts records a person found by searching. The backtest asks what the radar's own collectors would have seen.

## Checked against FracTracker Alliance's dataset

The owner said on November 23, 2026 to use FracTracker's data. Its spreadsheet was downloaded once that day. The file is kept outside this repository. Data provided by FracTracker Alliance (2026). Accessed via https://www.fractracker.org/data-centers/

- **FracTracker lists 98 records in the 30 counties.** 38 are operating buildings, 41 proposed, 14 approved or under construction, 4 expanding and 1 cancelled.
- **A program matched 72 of the 98 to 51 of the list's 126 projects of that day,** by a shared company or project name inside one county, or a point within one kilometer. The match is a machine's and has not been checked by a person. FracTracker often has one record a building where the list has one row a site.
- **26 records matched nothing.** 17 are operating buildings, most of them older than the list's 2023 cut for the urban counties. **Nine are proposed or approved** and went to a research pass, which started from FracTracker's own source links:
  - **Four are already in the list** under another name: one each in Dallas and Milam counties, one FracTracker places in Ellis County that the list has in Dallas County, and one Matagorda County record that covers two of the list's rows.
  - **Two were added,** each with no date and rated low. Land on State Highway 16 in Bexar County, left out earlier because no source then called it a data center: three trackers now do. And a 217 acre tract at Venus, keyed to Johnson County. **Its county is unsettled** between Johnson and Ellis. The city record that would date it sits on a meeting platform that is not cleared.
  - **One is outside the 30 counties.** Caldwell County's minutes of April 9, 2026 show talks on it. Only an unsourced listing says Travis County.
  - **One is left out as older than the cut:** a federal data center in San Antonio first reported in 2007.
  - **One is left out as marketed land:** a parcel in a land broker's sales deck near Midlothian and Venus, with no operator and no record.
- **75 of the list's projects have no match in FracTracker's file.**
- **FracTracker lists nothing in the eleven control counties,** and nothing in the five test counties where the list has no project: Burnet, Erath, Falls, San Saba and Wise.
- The file gives no date a project became public, so it changes no date here.

## Left out, and why

- **Rumors.** Erath County: land on two county roads, no developer and no record. Marlin in Falls County: the mayor says the city was approached, nothing in writing.
- **Land with no data center announced.** A power company's tract near Red Lick in Bowie County. Its tract on State Highway 16 in Bexar County was left out at first and added on November 23: see the check against FracTracker's dataset.
- **Marketed sites.** A broker's 190 acres at Glen Rose and about 212 acres for sale in the city of Burnet.
- **A designation, not a project.** Land at the former army depot in Bowie County named a data center park in 2023.
- **Sites no source calls a data center.** A 20 MW crypto mining site in Wise County that only trackers file as one.
- **One undated tracker listing** in Travis County, with no address.
- **County unclear or outside the 30.** A tracker places one project in Richland Springs and three other sources place it elsewhere. Projects in Hale, Jack, Tarrant, Randall, Shackelford, Medina, Bastrop and Brazoria counties were reported near the test counties and left out.

## Sites treated as closed

`known_projects_hosts.csv` holds the robots result for every site a read in the list rests on. Each file was read once on November 22, 2026 with the project's own user agent. A test refuses a read that rests on a closed site.

A site is closed when its robots file:

- bars every program on the path, or
- bars an AI reader that acts for a user, under any name, or
- does not answer. A 404 means there is no file and the site is open.

A file that names only training crawlers does not close a site.

**What that rule set aside: 22 cited lines in 17 projects.** Each lost its date and needs a person to read the page.

- Some research passes read sites whose files bar AI readers under names other than the reader they used. Four television stations fall here. Six first reports rested on them: two in Henderson County, two in Ellis, one in Lubbock and one in Carson.
- **The trial did not check robots files at all.** The audit closed six of its sites: a trade paper, a television station, two newspapers, a property data site and a company's investor site. Thirteen cited lines in eight Hill, Hood and Milam projects are set aside, among them the first reports behind two of the trial's longest leads.
- Six pages in Hood County were read against a block in the trial and were set aside then. Two Hood County projects have no usable first record for that reason.
- One Bexar County row is set aside because the page read turned out to carry a story from a paper behind a subscriber wall.

**A reprint is the paper's page.** Passes did not open a Yahoo, AOL or MSN copy of a story from a paper that is barred, refuses or sits behind a subscriber wall.

## Slips the passes reported

No date in the list rests on any of them.

- Two requests to one host in the same batch, three times.
- A robots file fetched after the page it covers, four times. Each turned out to allow the read.
- Three pages opened before the pass knew they carried a closed paper's story.
- Waits between requests to one host were not timed. They rest on the time between steps.
- One pass ran 31 searches against a ration of 30.

## Not verified

- **Whether any county's list is complete.** Officials in Hill, Freestone, Parker, Tom Green and Lubbock counties spoke of more projects than were found. A newspaper counts 23 planned in Bexar County and 15 are listed.
- **The first report for 49 projects.**
- The day a government record could first be seen online. Minutes carry the day of the meeting, and in Archer County a file was made eight weeks after it.
- Whether a state registration covers the whole campus. Many are for one building.
- Street addresses and coordinates. 41 rows have a point, most from the Census geocoder for a street address.
- **The second read, for the 27 later counties:** 85 cited lines held, 11 showed a gap in wording or place, 2 could not be opened and 6 state registrations in Harris County were not sent. No date differed. In the trial, the session itself re-opened nine sources and every date held. Some of those nine are now set aside, because the site is closed.
- Whether two Hill County entries, Project Aquila and the C.R. 3106 project, are one project.

## Leads for a person

- **Parker County.** A state air registration for gas turbines, said to describe bridge power for a data center, from about April 2025. That would be about 13 months before the first news. The state site is barred to programs. Identifiers are in the row's notes and are unverified.
- **Hopkins County.** Council minutes are said to put a city letter of intent on December 19, 2024, six months before the company's release.
- **Archer County.** The code name alone is on a county agenda posted September 16, 2025.
- **Dallas County.** Seagoville rezoned 138 acres for a data center on November 18, 2024. No news report was found.
- Code-named abatement items with no use stated, on a Hopkins County agenda of September 22, 2026 and in Taylor County minutes of November 18, 2025.

## Cost

28 research passes, one pass to finish searches a shared limit cut short, and four second-read passes. About 8 million tokens and about 850 web searches in all. Each county took 5 to 19 minutes.
