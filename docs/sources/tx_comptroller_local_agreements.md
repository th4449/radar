# Comptroller local development agreements

- Source id: `tx_comptroller_local_agreements`
- Page: https://comptroller.texas.gov/economy/development/search-tools/sb1340/
- Checked: November 19, 2026
- Result: **allowed.** Manual until the first fixture is saved and a collector is written in M2.

## What was verified

- **Robots rules.** The overview, the search form and the results address are all under `/economy/`, which `comptroller.texas.gov/robots.txt` allows. No second host is involved.
- **Reuse.** The Comptroller's privacy and security policy calls information on its sites public domain. See `tx_comptroller_data_centers.md`.
- **The search.** A plain form with no captcha and no login. Fields: government type, government name, agreement type and entity name. Agreement types include abatement and reinvestment zone.
- **Stated by the page.** All information is provided by local governments. Chapter 380 and 381 agreements with no set end date display as 2078-12-31.

## What was not verified

- The results page was not requested. Its layout, paging and where agreement documents are hosted are unknown.
- Whether the Comptroller's open data pages carry this database as a file.

## Notes for the collector

- This record lags. Chapter 312 reports are due July 1 of the following year. Its value is the history: which governments, companies, consultants and law firms recur.
- Query by government name for the bodies in the 30 counties, once a month. Do not sweep every name.
