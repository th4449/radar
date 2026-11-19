# Texas Comptroller registered data centers

- Source id: `tx_comptroller_data_centers`
- Layer: baseline of known sites
- Page: https://comptroller.texas.gov/taxes/data-centers/data-center-lists.php
- Checked: November 19, 2026
- Method: manual for now. Intended method is plain HTTP once the first fixture is saved and a collector is written in M2.

## What was verified

- **Robots rules.** `https://comptroller.texas.gov/robots.txt` closes every folder with `Disallow: /*/` and then opens a list of folders again. `Allow: /taxes/` and `Allow: /economy/` are on that list. The data center list is under `/taxes/`, so it is allowed. The file sets no crawl delay.
- **Reuse.** The Comptroller's Privacy and Security Policy says: "Information on CPA's sites is public domain and may be copied and used as permitted by law, with the exception of pictures, official symbols, and registered service marked names and logos."
- **Automated access.** The policy page has no sentence about automated access, robots or scraping.

## What was not verified

- The list page itself has not been opened by our fetcher. Its structure, file formats and update rhythm are unknown.
- The build plan says the list has no county field. Not yet checked by us.
- `mycpa.cpa.state.tx.us`, the franchise tax search used for entity lookup, is a different host. Its robots rules and terms were not read.

## Notes for the collector

- Our fetcher follows the wildcard and longest-match rules in this robots file. `tests/test_fetcher.py` has a test built on the same pattern.
- The same robots file and policy cover `tx_comptroller_local_agreements`, which is under `/economy/`. That source still needs its own note before a collector is written.
- Low cadence. The list changes rarely, so once a month is enough.
