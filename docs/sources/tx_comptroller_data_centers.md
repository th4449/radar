# Texas Comptroller registered data centers

- Source id: `tx_comptroller_data_centers`
- Layer: baseline of known sites
- Page: https://comptroller.texas.gov/taxes/data-centers/data-center-lists.php
- Checked: November 19, 2026
- Method: **saved by a person, once a month, since November 23, 2026.** No job reads it. See "Saved by hand". Before that: plain HTTP. Collector and parser: `collectors/tx/comptroller_data_centers.py`.
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

## November 23, 2026: the site refused the collector

- The collector was run once, to give the backtest's history its own copy of the list. **It stored nothing.** The fetcher asked for `https://comptroller.texas.gov/robots.txt` and got a 403, and the fetcher treats a robots file it cannot read as a closed site.
- One more request for the robots file, with the same user agent, got the same answer: a 403 page with the message code `CTG-CF-403`. Two requests in all. Nothing else was tried.
- On November 19 the same address answered 200 and allowed `/taxes/`.
- **Not verified:** whether the refusal is lasting, and whether it is aimed at the collector's user agent, at this connection or at every program.
- The backtest uses the copy saved with the tests on November 19, 2026. That is the real page of that day.
- The owner said on November 23, 2026 to ask once more on a later day, and later that day said to give the site a run.
- **That run, at 11:46 UTC on November 23, was refused the same way.** One request, for the robots file. Nothing was stored and nothing else was tried. That makes three requests for the robots file that day, about six hours apart, all refused.
- A second refusal on the same day does not show whether the refusal is lasting.
- **The owner marked the source manual the same day.** See "Saved by hand".

## Saved by hand

The owner's decision of November 23, 2026. In `config/sources.yaml` the source is `method: manual`, `robots_status: blocked` and `hand_saved: true`. The fetcher refuses it, by a job or by hand, and its workflow file is gone.

**What a person does, about once a month**

1. Open https://comptroller.texas.gov/taxes/data-centers/data-center-lists.php in a browser.
2. Save the page as "Webpage, HTML only". Not a web archive and not a PDF.
3. Run the command on the saved file, with `DATABASE_URL` and `RADAR_ARCHIVE_DIR` set as for a real run:

   ```
   uv run python -m collectors.by_hand tx_comptroller_data_centers ~/Downloads/data-center-lists.html
   ```

**What the command does**

- It makes no request.
- It reads the file with the collector's own parser. A file that is not the page with its two tables is refused and nothing is stored: the site's refusal page, a browser's archive format, the wrong page.
- It stores the file with the page's address, the time and the file's hash, as a run does, and the record says a person saved it. The time is the file's own unless `--saved-at` gives another. The file's name is not kept.
- The rules then use the newest stored copy, whoever stored it.

**The first page saved by hand, November 23, 2026**

- The owner saved the page at 13:10 UTC and it was stored the same hour in the backtest's history database, the only store that exists so far. 148,721 bytes, SHA-256 `87bec5f3cd0fd313de98a8c71efe264cdc38971065f0b3ef3ce0b4b38e8b156a`.
- **The parser read it:** 70 registered qualifying data centers and 119 large projects, 189 in all. That is six more large projects than on November 19, with effective dates from November 6 to November 16, 2026. None is gone.
- The backtest now reads this copy. Its result did not change.

**The first page stored in the hosted project, November 26, 2026**

- The owner saved the page from Chrome as "Webpage, HTML Only" at 22:23 UTC and stored it two minutes later with `scripts/store_by_hand_hosted.py`. A first save, as a complete webpage, was set aside and not stored: its links were rewritten to a local folder.
- 150,699 bytes, SHA-256 `3b444dcf7e95d4913cfaff9ff1fd37eedbf0144142be283123fa1c2854980b87`. The file on the owner's machine hashes to the same value, and the archive reports the same size.
- **The parser read it:** 195 registrations, six more than on November 23. 70 registered qualifying data centers and 125 large projects. The six more are all large projects. The newest effective date is November 19, 2026. The six were not compared name by name with the copy of November 23.

**Not verified**

- Which browser and which save format the owner used on November 23. One page saved from a browser has been read. Another browser's save may differ. If the parser refuses one, nothing is stored and the command says so.
- Whether the site would answer a job again. To find out, the owner sets the source back and one run asks.
