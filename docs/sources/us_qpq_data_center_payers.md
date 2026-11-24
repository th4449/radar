# QPQ Tracker study of who paid for the data centers: its list of payers

- Source id: `us_qpq_data_center_payers`
- Layer: baseline. A list of companies, not of sites and not a signal.
- Page: https://www.purchasingpolicy.org/data-centers
- Checked: November 24, 2026
- Result: **allowed, and manual.** The page is open to a collector. No job reads it. The method stays manual until the owner says to run it.
- Collector and parser: `collectors/us/qpq_data_center_payers.py`
- Fixture: `tests/fixtures/us_qpq_data_center_payers/data-centers-payers.html`, the page's table of payers, cut from one copy saved on November 24, 2026 with one request through `collectors.capture`.

The QPQ Tracker is a project of Anti-Corruption Action, the organization that runs the radar. The rules for a source hold all the same.

## What was verified

- **Robots rules.** `https://www.purchasingpolicy.org/robots.txt`, read November 24, 2026. For every agent: `Allow: /`, then `Disallow` for `/compare`, `/money-flow`, `/israel-lobby`, `/sectors/` and `/api/`. The study page is under none of those, so it is allowed. Six named crawlers get the same rules and a crawl delay of 10 seconds. The radar's agent is not one of them.
- **The API is barred.** The build plan says to use the site's API. `Disallow: /api/` covers it. The API notes at https://www.purchasingpolicy.org/api-docs say the endpoints are public, need no key and "can be called directly". The two disagree. The radar goes by the robots file and does not call the API.
- **The API has no list of payers.** The notes list nine endpoints: a name search, an entity's connections, two flow graphs, giving by state, stock trades, policy events, one policy event and a health check. None returns the study's payers. This was read from the notes. No endpoint was called.
- **The study page holds the whole list.** A table headed "All 61 payers" has one row for each payer. It is in the page as served, so no browser is needed.
- **Terms.** The site has no terms of use page. `/terms` answers 404, and the About page links none. The About page states no terms for reuse of the site's own pages. It says the tracker "does not assert that any donation caused any outcome".
- **The owner's word.** On November 24, 2026 the owner said to build from the study page.

## What the page holds

Read from the saved copy.

- **61 payers.** Columns: payer, class, direct giving, contributions and states. Each payer's name links to its page in the study, at `/entity/` and an identifier.
- **Classes**, in the study's words: 35 "Utility", 12 "Trade group, developer, pipeline or investor", 8 "Data center operator" and 6 "Hyperscaler".
- **The rows add up to the page's own figures.** The page gives $148.4M in 16,389 contributions. The 61 rows sum to $148,392,563 and 16,389.
- **What the money is**, as the page says: corporate and employee PAC giving reported in the filing systems of 16 states, from 2023 to the latest filing. Michigan and Texas are among the 16.
- 17 payers have giving in Texas or Michigan filings.
- **Names are the study's labels.** Some join two names, such as "CMS / Consumers Energy" and "Exelon (ComEd, PECO)". Some are ordinary words: "Switch", "Meta", "Oracle".
- The page also lists officeholders, candidates, measures and votes. The radar reads none of that. The fixture keeps only the table of payers.

## What the radar does with it

- It keeps a copy of the page with its address, retrieval time and hash, like any document.
- It checks whether a company on record has the same name as a payer. The rules are in `pipeline/study.py` and `config/study_payers.yaml`.
- A match says the company's name is in the study. It says nothing about a site.

## Companies the study's page does not name

Added on November 24, 2026, on the owner's word. A record names an operating company more often than its parent: "DTE Electric Company", not "DTE Energy". 45 such names for 16 payers are in `config/study_payers.yaml`, each with the filing that states whose it is.

- **Where they come from.** 38 are in a list of subsidiaries or an annual report the company itself filed with the SEC. Three are named as a subsidiary in another company's SEC filing. Three are on the company's own site. One, Walbridge Aldinger LLC, is in a City of Detroit record.
- **How the SEC was read.** `https://www.sec.gov/robots.txt` has `Allow: /Archives/edgar/data`. The SEC answers a request that says who is asking and refuses one that does not. Each of the 20 filings was fetched once, by hand, with a user agent that gives the project's public contact address, three seconds apart. The words were read in the saved copy.
- **What was read another way.** The two company pages and the Detroit record were read with a web reading tool, not as raw files. The company's own site writes "Walbridge Aldinger" with no legal form.
- **A name with its legal form meets a record only as written.** "DTE Electric Company" meets "DTE Electric Co." and not "DTE Electric LLC".
- **On the Comptroller's saved list** of 290 companies, 5 met a payer before and 19 do now.

Left out, each for a reason:

- **Numbered project companies**, such as "Vantage Data Centers TX11, LLC" and "QTS Irving DC3, LLC". No filing was found that states whose they are.
- **Project companies that only news reports tie to a parent.**
- **Electric Transmission Texas, LLC.** AEP's annual report calls it a joint venture with Berkshire Hathaway Energy.
- **Holding companies**, and subsidiaries whose work the filing does not state.

Not verified:

- Whether each filing is still current. Switch's is its annual report for 2021, the last one found.
- **Oncor.** Its annual report for 2025 says a Sempra subsidiary owns 80.25% of it. Sempra is a separate payer in the study. Nothing was changed for that.
- A name that only looks like a payer's can still match. A company called "Black Mountain Power Company LLC" would meet the payer "Black Mountain Power". Whether such a company exists was not checked at its source.

## Rules the collector keeps

- One request for one page. Once a month is enough.
- The payers' own pages are not fetched. The radar links to them.
- If the table, its columns, a row's shape or its count changes, the parser stops with `LayoutChanged` and nothing is stored.
- The page's count must equal the table's length. A shorter table is not the whole list.

## What was not verified

- How often the study's list changes. The page says its figures were re-derived on October 22, 2026.
- Whether the site answers GitHub's servers. The one request came from a desk.
- Any endpoint of the API. None was called.
- The robots file, the API notes and the About page were read with a web reading tool, not the radar's fetcher. The fetcher read the robots file itself before it took the fixture, and went on.
