# Comptroller local development agreements

- Source id: `tx_comptroller_local_agreements`
- Page: https://comptroller.texas.gov/economy/development/search-tools/sb1340/
- Checked: November 20, 2026
- Result: **held. Manual for now.** The search pages are open. The data behind them sits on two other hosts whose robots files cannot be read, so our fetcher refuses them. No collector is written. **The owner sent the request to the Comptroller on November 23, 2026. No answer yet.**

## What was verified

- **The search pages.** The overview, the search form and the results page are under `/economy/` on `comptroller.texas.gov`, which that site's robots file allows. All three were fetched once each. The form has no captcha and no login. Its fields are government type, government name, agreement type and entity name.
- **Reuse.** The Comptroller's privacy and security policy calls information on its sites public domain. See `tx_comptroller_data_centers.md`.
- **The results page holds no data itself.** It is an empty frame. A script fills four tables from a data service at `api.comptroller.texas.gov/open-data/v1`, and adds download buttons.
- **The download buttons** point to seven CSV files on a third host, `assets.comptroller.texas.gov/open-data-files/`: `ch380.csv`, `ch312-abatement.csv`, `ch312-abatement-zone.csv`, `ch312-abatement-report.csv` and a "detail" file for each of the last three. Read in a browser, as a visitor sees the page.
- **Size of the database**, from the page's own counts after one search: 4,397 Chapter 380 and 381 agreements, 1,490 abatements, 1,255 reinvestment zones and 991 post-abatement valuations.
- **Freshness.** The server reported `ch380.csv` as 3,973,041 bytes, last modified November 19, 2026. Only its headers were requested. The file was not downloaded.
- **One search was run**, for "Hood". It returned one agreement, one abatement, one zone and one valuation, all naming power generation companies.

## Why it is held

- **`api.comptroller.texas.gov/robots.txt` answers 403**, as does every other address on that host that is not a data call.
- **`assets.comptroller.texas.gov/robots.txt` answers 403** with "Access Denied". The CSV file next to it answers 200.
- **Our fetcher reads a refusal on a robots file as "do not proceed".** It stopped before requesting the CSV, as it is built to.
- **The likely cause is plain.** Both hosts are file and gateway services that answer 403 for any address that does not exist. Neither appears to publish a robots file at all. That is a reading, not a fact we can confirm from outside.
- We do not work around a refusal. Whether these two hosts may be treated as "no rules published" is the owner's decision, best made with the Comptroller's answer in hand.

## Timing: not all of it lags

The earlier note called this record lagging. That is half right. The overview page says:

- **Chapter 380 and 381 agreements** must be reported within 14 days of being entered, amended or renewed. These are the cities' and counties' economic development deals. This part can be an early signal.
- **Chapter 312 abatements and reinvestment zones** are due before July 1 of the year after. This part lags by up to 18 months.
- Only agreements active on September 1, 2021 or made since have to be reported.
- For agreements with no end date, the expiration shows as 2078-12-31.
- All information is provided by local governments.

## Options for the owner

1. **Ask first. Recommended, and done:** the owner sent the note to the Comptroller's transparency office. It asks whether a monthly download of the seven published CSV files is acceptable and whether the hosts have robots rules. Until an answer comes, a person downloads the files with the page's own buttons when needed.
2. **Stay manual.** A reviewer downloads `ch380.csv` once a month by hand. Seven clicks cover everything.
3. **Approve an exception without asking.** Name the one host in config as publishing no robots rules, and collect the seven files monthly. The files are public, linked from a public page and called public domain. It still changes how the fetcher reads a refusal, for that host only.

Seven requests a month would cover the whole database. No search sweep is needed.

## What was not verified

- The contents of any CSV file: its columns, whether it carries the agreement date and whether it names private individuals as property owners.
- Whether the files are rebuilt daily. One file's date suggests it.
- The detail pages, such as `economic-development-agreements-details.php?agreement=...`, and whether they link the agreement documents.
- The request and response of the data service. It was not called outside the page.
- Whether the Comptroller's open data portal carries the same tables.

## Notes for a collector, if one is approved

- Fetch the seven CSV files with the ETag of the last copy, once a month. Chapter 380 and 381 could justify weekly, given the 14-day rule.
- Filter to governments in the 30 counties after download.
- Property owners in abatement records can be individuals. The check that holds back rows naming a person applies here too.
