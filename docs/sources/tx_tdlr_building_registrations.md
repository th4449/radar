# TDLR building project registrations

- Not a source yet. **Proposed, for the owner to decide.** It is not in `config/sources.yaml` and nothing collects it.
- Page: https://www.tdlr.texas.gov/TABS/Search
- Checked: November 22, 2026
- Result: **nothing found against a slow collector.** The search itself is untested.

## Why it is here

The plan does not list this source. The list of known projects found it by itself: 34 of its dated records are registrations on this site, more than any other kind of record. See [known_projects.md](../../backtest/known_projects.md).

Texas requires a building project above a cost threshold to be registered with the Department of Licensing and Regulation for an accessibility review. A registration is public and carries a project name, an address, an owner, a cost and dates.

## What was read

- **Robots rules.** `https://www.tdlr.texas.gov/robots.txt`, read with the project's user agent: one group for all agents. It closes `/ithelp/`, every address ending in `.csv` and four forms. It leaves `/TABS/` open. No crawl delay.
- **Terms.** The policy page at https://www.tdlr.texas.gov/disclaimer.htm, linked from the search page's footer, SHA-256 `cdd5f24acdfa5933d875c64dad5f09f2525e9c55f96bd74edd527bdfeda329f8`.
  - It says nothing about automated access.
  - Its link policy is the state's: information on a state agency site may be copied if it is shown in a way that does not mislead and does not imply the state endorses the copier. Copied information must show the agency's rights in it.
  - It warns against putting a download burden on the agency's servers.
  - The agency's logos need permission. The radar uses none.
- **Three requests in all:** the robots file, the search page and the policy page.

## What follows from the robots file

- **The search's spreadsheet export is closed to programs.** Any address ending in `.csv` is barred. A collector would have to read result pages and registration pages, one at a time.

## What the known-project list says about its timing

- For 18 projects, a government record and the first news report were both read on the page. Nine records came after the news. **Six of those nine are registrations.**
- A registration is filed when a building is designed. That can be long after a campus is announced.
- So this is likely a late signal for a first building and may be an early one for a later phase. The backtest can measure it only if registrations are collected.

## Not verified

- How the search works for a program: whether it can be asked by county and date, how many results a page holds and whether it needs a session.
- Whether a registration can be found before its review is complete.
- How many registrations a year fall in the 30 counties.
- **Whether owners are people.** The owner field can name a person for a small project. The source would need `personal_rows`.
- Whether the agency has an open data file of registrations elsewhere. None was looked for.
