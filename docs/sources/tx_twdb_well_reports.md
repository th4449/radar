# TWDB submitted drillers reports

- Source id: `tx_twdb_well_reports`
- Page: https://www.twdb.texas.gov/groundwater/data/data-well-reports.asp
- Checked: November 20, 2026
- Result: **allowed, and held.** Nothing restricts automated access. No collector is written. The owner has to decide what the radar keeps from this file first. See "The decision" below.

## What was verified

- **The page moved.** The URL in the build plan, `drillersdb.asp`, now shows a notice pointing to the page above.
- **Robots rules.** `https://www.twdb.texas.gov/robots.txt` closes only `/calendar/`. No crawl delay.
- **Reuse.** The site policies page says the board "freely grants permission to copy and distribute its materials" and would appreciate acknowledgment.
- **Monitoring.** The same page says the site is monitored and that attempts to upload, change or damage are prohibited. Nothing on robots, crawlers or scraping.
- **Data caveat stated by the board.** Well locations are not verified by state staff and may be inaccurate. Reports mailed in before the online system are not included.

## The bulk file, read on November 20, 2026

The page links `/groundwater/data/SDRDownload.zip`. It was downloaded once by hand: 152,513,192 bytes, retrieved 2026-11-20T07:16:32Z, SHA-256 `5ade64a6da29f45409ab324ba2faf89ef89fead321048f76737d9836a56d7de8`. The copy was read and then deleted. It is not in the repository.

- **Size.** 145 MB zipped, 823 MB unpacked. The fetcher refuses anything over 50 MB.
- **Freshness.** The server gave a Last-Modified of November 19, 2026 and an ETag. The tables inside are dated November 18, 2026.
- **Contents.** 22 pipe-delimited text tables and a ReadMe folder. The ReadMe explains how to import the tables. It sets no terms.
- **The main table, `WellData.txt`.** 715,155 reports and 73 columns. Among them: tracking number, date submitted, owner name, owner mailing address, county, well address, coordinates, type of work, proposed use, drilling start and end dates, driller company and driller name, and a comments field.
- **Encoding.** The text is Windows-1252, not UTF-8. Lines end in CRLF. Four rows have an extra field, most likely a pipe character inside a comment.
- **Proposed use.** Domestic 293,000. Monitor 126,799. Environmental soil boring 87,579. Irrigation 75,473. Stock 36,368. Rig supply 35,171. Test well 24,038. Industrial 9,664. Public supply 6,435. Seven smaller groups.

## What it shows for the radar

- **The 30 test counties** hold 194,368 of the reports. 13,737 were submitted since January 1, 2025, and 804 in the 30 days before the download.
- **Data center operators do appear.** Reports from 2026 name, as owner, a data center company with a public supply well in Bosque County, another with ten monitor wells in Travis County, and others in Williamson and Stonewall counties. They are filed under several uses: public supply, industrial, monitor and irrigation.
- **It is a late signal.** For reports submitted since 2025 in the 30 counties, the report arrived a median of 36 days after drilling ended. One in ten arrived more than 100 days after. A well is drilled before its report exists.

## Private individuals

- **About 41 percent of the reports are domestic wells.** Those rows carry a person's name and, in most cases, a home mailing address and the well's address and coordinates.
- Stock and irrigation wells are often owned by individuals too.
- Every row names the driller. A driller is a licensed professional, and still a person.
- The radar does not publish names of private individuals. The earlier note also said to store only what a signal needs.

## The decision

The build plan lists this feed as "downloadable" and the config has it as daily. Building it as the other collectors are built would mean:

- raising the size limit for one source,
- downloading 145 MB a day from the board, and
- keeping every day's copy of a file that holds the names and addresses of about 293,000 households. That is 53 GB a year in the archive.

That is more than a medium-weight, late signal needs. Options:

1. **Weekly, and keep an extract only. Recommended.** Download the file once a week, read `WellData.txt` and keep only rows that are in the 30 counties, are not domestic or stock wells and were submitted in the last two years. Drop the owner's mailing address from what is kept. Record the file's URL, retrieval time and hash, and do not keep the file. A reviewer traces a row by its tracking number. This departs from the rule that the original is archived, so it needs the owner's approval.
2. **Weekly, and keep the whole file.** Simplest to trace. 7.5 GB a year, and the archive holds every household.
3. **Leave it manual.** A reviewer checks the board's map viewer for a site already flagged by another signal. No download.
4. **Daily, as the plan says.** Option 1 or 2 at seven times the traffic. The 36-day lag means a daily run finds little a weekly run would miss.

Under option 1, rows owned by a person still get through under uses such as irrigation or monitor. The M4 check that holds back rows naming a person, already needed for the TCEQ list, would cover these too.

## What was not verified

- The other 21 tables. Only `WellData.txt` was read.
- The 45 MB shapefile of well locations, `SDRDB_well_locations.zip`. It is under the size limit. Its size and date were read from the server. Whether it carries owner names and the proposed use is not known.
- Whether the board publishes a file of changes only. None is linked.
- Whether each report has a public address a reviewer can open from its tracking number.
- `locwwrep.asp`, the guide to locating a well report.
- The lookup and map applications on `www3.twdb.texas.gov`. That host has no robots file.
- How often a report is corrected after it is submitted.

## Notes for the collector, once the owner decides

- One request for the zip, with the ETag of the last copy. An unchanged file costs one short answer.
- Read the table as Windows-1252 and stop with a clear error if the 73 column names change.
- Test fixtures must be a small table built from rows owned by companies and public bodies, with the driller's name blanked. No real household row goes in the repository.
- Credit the Texas Water Development Board.
