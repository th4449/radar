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
- **The first real run,** November 26, 2026, started by hand on GitHub on the owner's word: 18 documents seen, 18 new, no errors, in 91 seconds. All 18 are in the hosted database and archive. Two are the working group's agendas as spreadsheets, kept whole and stored without text: the reader takes no text from a spreadsheet. Run: https://github.com/th4449/radar/actions/runs/45889963738.

## Slide decks and zip files

Text is now read from slide decks, from Word files and from the files inside a zip. It was checked by hand on two real ERCOT files on November 20, 2026. Neither is committed, because each is over 4 MB.

- **A slide deck from the working group**, `/files/docs/2026/11/18/6.-ERCOT_LIOO_Portal_20261119.pptx`: 4,600,178 bytes, SHA-256 `658f532e0cfbe6a32aaff585ff22450a96313b1122ef29ad1087ee19509836d8`. Text came out of all 8 slides, with speaker notes.
- **The committee's zip file**, `/files/docs/2026/11/18/10.-Large-Load-Issues.zip`: 4,564,644 bytes, SHA-256 `65ef732dc9b22dc8594553e169515311a411e4dfc7666e75381bd6f8e62f7f33`. It holds one slide deck of 15 slides. Text came out of all 15.

## About the fixtures

- The two index pages name each committee's chair and vice chair with a work email address, and an ERCOT staff contact, as ERCOT publishes them.
- The meeting pages name presenters and carry the public Webex dial-in details.
- The secret scanner runs on them in CI. It is not installed on the machine that saved them.

## What was not verified

- Text inside pictures and embedded chart objects. Both decks that were read hold charts as embedded objects, so numbers shown only in a chart are not in the extracted text.
- Spreadsheets. They are stored with no text extracted.
- Whether a committee file about large loads can carry a title without those words. The filter would miss it.
- Whether the working group's queue update is posted anywhere when it is not on an agenda.
- Earlier years. Each index links to pages for past years, such as `/committees/tac/llwg/2025`. They were not read.
- A run from GitHub's servers. ERCOT's site sits behind a screening service.
- The community impact survey update named in the build plan, `Community-Impact-RFI-PUC-Update.pdf`. It was not fetched, and no page that lists it was found.

## Other notes

- These reports are aggregate. They can say that load requests in a zone grew. They cannot say where a site is.
- ERCOT runs an email list for the working group. A reviewer can subscribe as a cross-check.
