# TWDB submitted drillers reports

- Source id: `tx_twdb_well_reports`
- Page: https://www.twdb.texas.gov/groundwater/data/data-well-reports.asp
- Checked: November 19, 2026
- Result: **allowed.** Manual until the first fixture is saved and a collector is written in M2.

## What was verified

- **The page moved.** The URL in the build plan, `drillersdb.asp`, now shows a notice pointing to the page above.
- **Robots rules.** `https://www.twdb.texas.gov/robots.txt` closes only `/calendar/`. No crawl delay.
- **Reuse.** The site policies page says the board "freely grants permission to copy and distribute its materials" and would appreciate acknowledgment.
- **Monitoring.** The same page says the site is monitored and that attempts to upload, change or damage are prohibited. Nothing on robots, crawlers or scraping.
- **Bulk download.** The page offers the full database as one file, `SDRDownload.zip`, on the same host. It says the file holds pipe-delimited text tables with a ReadMe folder and is updated nightly. Shapefiles of well locations are offered too.
- **Data caveat stated by the board.** Well locations are not verified by state staff and may be inaccurate. Reports mailed in before the online system are not included.

## What was not verified

- The zip file was not requested. Its size, date and ReadMe terms are unconfirmed.
- `locwwrep.asp`, the guide to locating a well report.
- The lookup and map applications on `www3.twdb.texas.gov`. That host has no robots file. We do not need them if the bulk file works.

## Notes for the collector

- One request for the zip file, at most once a day. No page crawling. Check the size first with a conditional request, because the fetcher refuses bodies over 50 MB and that cap may need raising for this one file.
- Filter to the 30 counties after download, then by drill date, owner and proposed use.
- Owner names in this database are often private individuals. Store only what a signal needs, and never publish an individual's name.
- Credit the Texas Water Development Board.
