# TDLR building project registrations

- **Proposed as a source on November 23, 2026, at the owner's request.** It is in `config/sources.yaml` as `manual` and nothing collects it. The build plan's table of sources does not list it yet.
- Page: https://www.tdlr.texas.gov/TABS/Search
- Read: November 22, 2026. Three requests in all: the robots file, the search page and the policy page. Nothing was asked of the site on November 23.
- Result: **nothing found against a slow collector, with one open question the owner decides:** the search answers only through the page's own script call. See "The question".

## What it is

Texas requires a building project above a cost threshold to be registered with the Department of Licensing and Regulation for an accessibility review. A registration is public. It carries a facility name, an address, a city and county, an owner, a cost, the kind of work and dates. Each has its own plain page, such as `/TABS/Search/Project/TABS2023021880`.

## Why propose it

**It is the record the list of known projects leans on most, and the backtest shows the gap it would fill.**

- 34 of the 128 known projects have a registration as their earliest dated record. No other kind of record is as common. 28 of the 34 were read twice.
- **They sit where agendas show nothing:** 15 in Dallas County, 10 in Bexar, 6 in Harris. In the backtest, twelve judged projects sit where the radar held the county's or the city's agendas. Eight are in Dallas and Harris counties, and for six of those the earliest record found is a state filing or the company's own release. A data center in a large city often needs no vote.
- **13 of the 34 have no news report at all.** The registration is the only dated record found.
- **For 21, both the registration and the first news report are dated.**
  - In 13 the registration came first, by 1 to 918 days. Nine of those leads are three weeks or less.
  - In 8 it came the same day or after, by up to 641 days.
  - The median is a registration two days ahead.
- **What that suggests, and it is not verified:** trade reporters read these registrations, and a story often follows one within days. A radar that reads them would see a building about when the trade press does, and sometimes long before.

## What it would not do

- **It is late for a campus.** A registration is filed when a building is designed. A campus can be announced a year or more before its first building is registered. Six of the nine late records in the list's own comparison are registrations.
- It would catch a later phase or a new building on a known campus early. Whether that is worth an alert is the reviewers' call.
- It names buildings, not land deals or rezonings.

## What was read

- **Robots rules.** `https://www.tdlr.texas.gov/robots.txt`, read with the project's user agent: one group for all agents. It closes `/ithelp/`, every address ending in `.csv` and four forms. It leaves `/TABS/` open. No crawl delay.
- **Terms.** The policy page at https://www.tdlr.texas.gov/disclaimer.htm, linked from the search page's footer, SHA-256 `cdd5f24acdfa5933d875c64dad5f09f2525e9c55f96bd74edd527bdfeda329f8`.
  - It says nothing about automated access.
  - Its link policy is the state's: information on a state agency site may be copied if it is shown in a way that does not mislead and does not imply the state endorses the copier. Copied information must show the agency's rights in it.
  - It warns against putting a download burden on the agency's servers.
  - The agency's logos need permission. The radar uses none.
- **How the search works,** read from the saved copy of the search page.
  - A form with filters for county, city, project status and two date ranges, one of them the registration date. A note in the page's source lists owner, facility, architect and address filters too.
  - **The results are not on the page.** A script asks `/TABS/Search/SearchProjects` and draws a table: status, facility name, city, county, kind of work and cost.
  - **The robots file bars any address ending in `.csv`.** If the search offers a spreadsheet export, it is closed to programs.

## The question

**A collector could find new registrations only by making the search's own script call.** The saved page holds no list of plain links, and a spreadsheet export is barred.

- Nothing read forbids it. The robots file leaves `/TABS/` open and the terms are silent.
- But the address is not a published interface, and the project has so far kept off a page's script calls. For the county calendars it reads the feed the page names, never the calls the page's script makes.
- Three ways forward:
  1. **Write to the agency first.** Ask whether a slow reader may use the search, or whether the agency can give registrations by county and date another way. Its registrations are public information. **Recommended.** It costs a letter and some days, and it settles the question instead of leaning on silence.
  2. Test the search with a few slow requests under the project's user agent, and build if nothing refuses. Faster, and it rests on the robots file alone.
  3. Leave it manual: a person searches by county each week and saves what a reviewer needs.

**The owner chose the first on November 23, 2026: write to the agency first.**

- **The owner sent the letter on November 23, 2026.** No answer yet.
- It was drafted for `Open.Records@tdlr.texas.gov`, the Public Information Coordinator in the Office of the General Counsel. The agency's policy page names that address for requests for information, read in the copy saved on November 22, 2026.
- The letter asks whether a slow reader may use the search, and otherwise for registrations in the 30 counties since January 1, 2023 as a file.
- **Until the agency answers, the search is asked nothing.**

## If the owner says yes

- A new kind of signal, with its own points in `config/scoring.yaml`. That file is the owner's to change.
- A registration needs a stated reason like any record: the facility name says "data center", or the owner is on the Comptroller's list. Most registrations are schools, shops and clinics.
- **The owner and architect fields can name a person.** The source is `personal_rows`, a record whose named party may be a person makes no signal, and the architect is never kept.
- One search a county a week is about 30 requests, plus one for each new registration that gives a reason. Not measured.
- Tests against saved pages, a slow pace and the project's user agent, as for every collector.

## Not verified

- Whether the search answers a program at all: its parameters, how many results a call holds and whether it needs a session. **The search has not been asked anything.**
- The cost threshold above which a project must be registered, and how soon before construction.
- Whether a registration can be found before its review is complete.
- How many registrations a year fall in the 30 counties.
- That reporters work from these registrations. It is an inference from the dates.
- The two longest leads in the list. The research pass that found the 918 day one says the registration may not be the same work as the announcement.
- Whether the agency publishes registrations as an open data file elsewhere. None was looked for.
