# TWDB submitted drillers reports

- Source id: `tx_twdb_well_reports`
- Page: https://www.twdb.texas.gov/groundwater/data/data-well-reports.asp
- Checked: November 20, 2026
- Result: **allowed.** Fetched over plain HTTP, weekly. The file is not kept. Each run stores an extract.
- Collector: `collectors/tx/twdb_well_reports.py`
- Fixture: `tests/fixtures/tx_twdb_well_reports/`, a hand-built sample
- Workflow: `.github/workflows/collect-tx-twdb-well-reports.yml`, started by hand only

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

The build plan lists this feed as "downloadable" and the config had it as daily. Built like the other collectors, it would have downloaded 145 MB a day and archived every copy of a file that names about 293,000 households, 53 GB a year. Four options were put to the owner: a weekly extract, the whole file weekly, manual only, or daily as planned.

**The owner chose the weekly extract on November 20, 2026.** This departs from the rule that the original file is archived.

## How the collector works

1. It asks for the zip file with the ETag of the last copy. An unchanged file costs one short answer.
2. It reads `WellData.txt` inside the zip and checks that the 73 column names are the ones read on November 20, 2026. If they are not, the run fails and stores nothing.
3. It keeps a row only if it is in one of the 30 test counties, is not a domestic or stock well and was submitted in the last 730 days.
4. From each kept row it keeps 23 columns: tracking number, date submitted, owner name, owner's well number, county, well address, city and zip, location description, number of wells, coordinates, type of work, proposed use, public water system number, drilling dates, comments and the numbers of linked reports.
5. It leaves out the owner's mailing address and every column about the driller: company, name, signature, license and address.
6. It stores the extract as text and records the board file's address, retrieval time, size and SHA-256 hash. The board's file is not written to disk, not even when a run fails on it.

The size limit for this one source is raised to 300 MB in `config/sources.yaml`. Every other source keeps the 50 MB limit.

A row with a stray pipe character cannot be split into its columns. It is not used. Its tracking number is recorded so a person can look it up.

## Verified live

- The download page, fetched once on November 20, 2026.
- The file, downloaded once by hand the same day to read its layout. That copy was deleted.
- One full run of the collector the same day, keeping nothing afterward. It read 715,155 rows and kept 8,325, from 29 of the 30 counties. It left out 74,333 household rows in the test counties, 111,710 older rows and 520,783 rows from other counties. Four rows were malformed. The extract is 1.5 MB. The run took 9 seconds and about 400 MB of memory.
- **The first real run,** November 26, 2026, started by hand on GitHub on the owner's word: `ok`, in 14 seconds. It read 715,668 rows and kept 8,358. It left out 74,415 household rows in the test counties, 111,755 older rows and 521,136 rows from other counties. Four rows were malformed, the same four. The extract is 1.5 MB, is in the hosted database and archive and is marked restricted. The board's file, 152,638,103 bytes, was not kept. Run: https://github.com/th4449/radar/actions/runs/45891285142.
- The kept rows by use on November 20, 2026: environmental soil boring 3,661, monitor 2,918, test well 554, irrigation 440, other 395, public supply 168, industrial 66 and seven smaller groups.

## What is still open

- **Kept rows can name a person. Handled in processing since November 20, 2026.** The stored extract is restricted: an administrator reads it, a reviewer does not. A row becomes a signal only when its owner's name shows a company or a public body. The comments and the location description are searched for terms and never copied whole. See `pipeline/signals.py`.
- **Soil borings and monitor wells are most of the extract.** Many belong to gas stations and cleanup sites. Whether they help or only add noise is a question for the backtest.
- **Each weekly extract is a full snapshot. Handled in processing.** A report already seen in an earlier extract makes no second signal.
- **Most kept rows make no signal.** A row needs a reason: its owner's name says "data center", uses a code word or matches a company on the Comptroller's registered data center list. A well drilled by a company with a new name and no such word is not caught from this feed alone.

## What was not verified

- The other 21 tables. Only `WellData.txt` was read.
- The 45 MB shapefile of well locations, `SDRDB_well_locations.zip`. It is under the size limit. Its size and date were read from the server. Whether it carries owner names and the proposed use is not known.
- Whether the board publishes a file of changes only. None is linked.
- Whether each report has a public address a reviewer can open from its tracking number.
- `locwwrep.asp`, the guide to locating a well report.
- The lookup and map applications on `www3.twdb.texas.gov`. That host has no robots file.
- How often a report is corrected after it is submitted.
- Whether a reviewer is refused the restricted extract on the hosted database. The policy tests have not run there.


## About the fixture

- No copy of the board's file is in the repository.
- The fixture is a 15-row sample built by hand. Its header line is the board's. Six rows are real reports owned by companies or a city, with the owner's mailing address replaced and every driller field removed. Nine rows are invented.
- Its `.meta.json` lists which rows are which.

Credit the Texas Water Development Board in anything published from this feed.
