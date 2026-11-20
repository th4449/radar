# ERCOT large load reports

- Source id: `tx_ercot_large_load`
- Index pages: https://www.ercot.com/committees/tac/llwg and https://www.ercot.com/committees/tac
- Checked: November 20, 2026
- Result: **allowed.** Fetched over plain HTTP, monthly. Context layer: totals by year and zone, no sites.
- Collector: `collectors/tx/ercot_large_load.py`, built on `collectors/tx/ercot_meetings.py`
- Fixtures: `tests/fixtures/tx_ercot_large_load/`
- Workflow: `.github/workflows/collect-tx-ercot-large-load.yml`, started by hand only

## Robots and terms

Same host, robots rules and terms as the Regional Planning Group files. See [tx_ercot_rpg.md](tx_ercot_rpg.md). The robots file does not close `/committees/`, `/calendar/` or `/files/docs/`.

## Where the reports are

The build plan gave two example files and no index page. Two committee pages list them.

- **Large Load Working Group.** Its index links one page per meeting, in the same layout as the planning group. On November 20, 2026 it listed 14 meetings for 2026. It also links to meetings of other bodies, in a table about a study process. The collector leaves those out.
- **Technical Advisory Committee.** It gets a large load update at most meetings. The plan's example file, `March-TAC-Report.pdf`, was posted for one. Its index listed 22 meetings for 2026 and 2027.
- **The "Large Load Integration" page** at `/services/rq/large-load-integration` was read too. It holds forms and guides for applicants, not reports. The collector does not use it.

## What the pages hold

- **The November 19, 2026 working group meeting** listed five files: an agenda, three PDFs and a slide deck, from 13 KB to 4.4 MB. None was a queue update that month.
- **The November 18, 2026 committee meeting** listed 14 files. One was about large loads: "10. Large Load Issues", a 4.4 MB zip file.
- **The form of the committee's update changes.** In March 2026 it was a PDF. In November it sat inside a zip file.

## How the collector works

1. It reads both indexes.
2. It reads each committee's meetings dated from 45 days back to 14 days ahead.
3. For a working group meeting it fetches every file listed.
4. For a committee meeting it fetches only files with "large load" in the title. The other files are never requested.

A file it already holds is asked for with its ETag. It keeps to one request every 5 seconds. If a page stops looking like the saved copies, the run keeps that page, fails and waits for a person.

## Verified live

- Six pages fetched once each on November 20, 2026 through `collectors.capture`: both indexes, the working group meetings of November 19 and December 17, the committee meeting of November 18 and the Large Load Integration page. Four are saved as fixtures.
- One dry run of the collector the same day: 18 documents, no errors. That is two indexes, four meetings and twelve files. A dry run keeps nothing.

## About the fixtures

- The two index pages name each committee's chair and vice chair with a work email address, and an ERCOT staff contact, as ERCOT publishes them.
- The meeting pages name presenters and carry the public Webex dial-in details.
- The secret scanner runs on them in CI. It is not installed on the machine that saved them.

## What was not verified

- **What is inside the zip file.** It is stored as it comes. Nothing reads inside a zip yet, so no text is extracted from it. That is work for M4.
- No slide deck or spreadsheet was opened. They are stored with no text extracted.
- Whether a committee file about large loads can carry a title without those words. The filter would miss it.
- Whether the working group's queue update is posted anywhere when it is not on an agenda.
- Earlier years. Each index links to pages for past years, such as `/committees/tac/llwg/2025`. They were not read.
- A run from GitHub's servers. ERCOT's site sits behind a screening service.
- The community impact survey update named in the build plan, `Community-Impact-RFI-PUC-Update.pdf`. It was not fetched, and no page that lists it was found.

## Other notes

- These reports are aggregate. They can say that load requests in a zone grew. They cannot say where a site is.
- ERCOT runs an email list for the working group. A reviewer can subscribe as a cross-check.
