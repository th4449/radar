# Texas Comptroller registered data centers

- Source id: `tx_comptroller_data_centers`
- Layer: baseline of known sites
- Page: https://comptroller.texas.gov/taxes/data-centers/data-center-lists.php
- Checked: November 19, 2026
- Method: plain HTTP, once a month. Collector: `collectors/tx/comptroller_data_centers.py`.
- Fixture: `tests/fixtures/tx_comptroller_data_centers/data-center-lists.html`, saved November 19, 2026 (UTC November 20) with one request.

## What was verified

- **Robots rules.** `https://comptroller.texas.gov/robots.txt` closes every folder with `Disallow: /*/` and then opens a list of folders again. `Allow: /taxes/` and `Allow: /economy/` are on that list. The data center list is under `/taxes/`, so it is allowed. The file sets no crawl delay.
- **Reuse.** The Comptroller's Privacy and Security Policy at https://comptroller.texas.gov/about/policies/privacy.php says information on its sites "is public domain and may be copied and used as permitted by law". It excepts pictures, official symbols and registered marks and logos.
- **Automated access.** The policy page has no sentence about automated access, robots or scraping.

## What the page holds

Read from the saved copy.

- One page with two tables: 70 registered qualifying data centers and 113 registered qualifying large data center projects.
- Columns: data center name, effective date, owner, occupant and operator names with their registration numbers, and exemption end date.
- **No county and no address.** The build plan said so and the saved copy confirms it. Placing these sites on a map needs another source.
- Every owner, occupant and operator is a company. No private individuals are named.
- The page has no download link for the lists. The tables are the data.
- The data has typing errors. Two effective dates read "06/172026". One row lacks its last cell. Some registration cells have stray spaces or a piece of the company name. The parser keeps the text as typed and leaves an unreadable date empty.

## What was not verified

- How often the state updates the page. It shows no update date. The newest effective date in the saved copy is November 5, 2026.
- Whether the registration numbers can be matched to a county through another Comptroller record.

## Notes for the collector

- Our fetcher follows the wildcard and longest-match rules in this robots file. `tests/test_fetcher.py` has a test built on the same pattern.
- The same robots file and policy cover `tx_comptroller_local_agreements`, which is under `/economy/`. That source still needs its own note before a collector is written.
- Low cadence. Once a month is enough for a baseline list.
- If the tables or their headers change, the parser stops with `LayoutChanged` and stores nothing.
