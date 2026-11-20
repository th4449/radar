# ERCOT Regional Planning Group project files

- Source ids: `tx_ercot_rpg` and `tx_ercot_large_load`
- Index page: https://www.ercot.com/committees/other/rpg
- Checked: November 19, 2026
- Result: **allowed.** `tx_ercot_rpg` is fetched over plain HTTP, weekly. `tx_ercot_large_load` has no collector yet.
- Collector: `collectors/tx/ercot_rpg.py`
- Fixtures: `tests/fixtures/tx_ercot_rpg/`
- Workflow: `.github/workflows/collect-tx-ercot-rpg.yml`, started by hand only

## What was verified

- **Robots rules.** `https://www.ercot.com/robots.txt` has one group for all agents and no crawl delay. It does not close `/files/docs/`, `/committees/` or `/calendar/`. It does close `/meetings`, `/widgets`, `/ical`, `/misdownload` and several `/content/` folders. Read again on the day the fixtures were saved.
- **Terms.** The Website User Agreement at https://www.ercot.com/help/terms, last updated July 20, 2023, says public contents may be used, reproduced and redistributed if they are not modified and notices are kept, and that raw data may be reused in compilations and analyses without the notices.
- **Limit on use.** The same agreement prohibits use that "negatively affects the performance of this website" and lets ERCOT block access. It says nothing about robots, crawlers or scraping.
- **The November 3 meeting page says** that all information is posted as public under ERCOT's content standard.

## What the pages hold

- **The index** links to one page per meeting under `/calendar/`. On the day it was saved it listed 28 meetings, for 2026 and 2027. Some meetings are linked twice, once as a rescheduled date.
- **A meeting page** has a title, a date, an agenda table and, once ERCOT posts them, a "Key Documents" list. Each file is under `/files/docs/<year>/<month>/<day>/` with a caption that gives the posting date, the type and the size.
- **The November 3, 2026 meeting** had three files, all PDFs, from 0.5 to 1.6 MB. The December 15 meeting had no agenda and no files yet.
- **The files** carry an ETag and a Last-Modified header. The pages do not.
- **The pages change a few bytes on every request.** Two tracking scripts carry codes that differ each time. The collector compares what a page says, not its bytes, so an unchanged page is not stored again.

## How the collector works

1. It reads the index.
2. It reads the meetings dated from 35 days back to 14 days ahead. Older meetings are settled.
3. It fetches each file those meetings list. A file it already holds is asked for with its ETag, so an unchanged file costs one short answer.

It follows no other link. It keeps to one request every 5 seconds. If a page stops looking like the saved copies, the run keeps that page, fails and waits for a person.

## Verified live

- Three pages saved through `collectors.capture`: the index and the meetings of November 3 and December 15, 2026.
- One file fetched by hand and not committed, because of its size: `/files/docs/2026/11/02/3.-EIR-Status-Update-26RPG004-AEPSC-Laredo-Area-Upgrade-Project_NovRPG_Final.pdf`, retrieved 2026-11-20T02:50:46Z, 1,628,860 bytes, SHA-256 `3c5625c8b17198237d01147ef5304b05d44390f0c6090a5f350022f28da93656`. Text came out of all 49 pages without OCR.
- One dry run of the whole collector on November 19, 2026. It read the index, the two meetings in its window and ten files, 13 documents in all, with no errors. A dry run keeps nothing.

## About the fixtures

- The index names two ERCOT staff contacts and the group's mailing list, as ERCOT publishes them.
- The meeting pages carry the public Webex dial-in details ERCOT posts for each meeting.
- A secret scan of the fixtures found nothing.

## What was not verified

- Meetings before 2026. The index shows the current and the next year. Where older years are listed is not known, and the backtest will need them.
- Whether ERCOT ever replaces a file under the same address. The conditional request would catch it.
- Files that are not PDFs. They are stored as they come, with no text extracted.
- A run from GitHub's servers. ERCOT's site sits behind a screening service. It answered our requests from a desktop connection. If it refuses a request, the run stops and a person decides.
- ERCOT's "Legal Policies and Notices" page at `/about/legal` was not read.
- No index page for large load reports was found. Those reports sit under `/files/docs/` like the others. The large load pages seen in the site navigation were not read.
- The ERCOT public API and data product pages. Whether they cover these files is unknown.

## Other notes

- ERCOT runs an email list for the group. A reviewer can subscribe as a cross-check.
- In September 2026 ERCOT said it was weighing whether to keep reviewing large load projects in this process. The feed may thin out.
