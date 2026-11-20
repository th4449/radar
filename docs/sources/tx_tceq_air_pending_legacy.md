# TCEQ pending air permit lists on the older site

- Source id: `tx_tceq_air_pending_legacy`. The new portal is `tx_tceq_air_pending`, with its own note.
- Start page: https://www.tceq.texas.gov/permitting/air/airpermit-applications-notices
- Checked: November 20, 2026
- Result: **allowed.** Fetched over plain HTTP, weekly.
- Collector: `collectors/tx/tceq_air_pending_legacy.py`
- Fixtures: `tests/fixtures/tx_tceq_air_pending_legacy/`
- Workflow: `.github/workflows/collect-tx-tceq-air-pending-legacy.yml`, started by hand only

## Two lists, and only one of them is frozen

Both pages sit under `/assets/public/permitting/air/reports/applications/`.

| Page | File | State on November 20, 2026 |
|---|---|---|
| New Source Review permits | `nsr-pending-permits.html` | "Data Updated: 8/28/2026". The page is rebuilt every day with a new "Report Run" date. |
| Title V operating permits | `titlev-pending-permits.html` | "Data Updated: 11/19/2026". Newest application received November 16, 2026. |

The start page says that from August 31, 2026 the Air Permits Division publishes New Source Review applications in the TCEQ Permit Search Portal. It says this of New Source Review only. The Title V list is still updated here.

An earlier version of this note said both lists stop at August 2026. That was wrong for Title V.

## What was verified

- **Robots rules.** `https://www.tceq.texas.gov/robots.txt` closes the site search and a few named paths. It does not close `/permitting/` or `/assets/`. A comment in the file says robots may access all areas already open to anonymous users. No crawl delay. Read again on November 20, 2026.
- **Reuse.** The linking policy says site content is considered public domain unless noted. The logo is excepted. TCEQ asks for acknowledgment.
- **Blocking.** The public access policy says TCEQ logs traffic and blocks activity that looks malicious or that threatens availability. Nothing on the policy pages mentions robots, crawlers or scraping.

## What the pages hold

- **One table each**, five columns: applicant, facility or area name, permit number, received date and a link to the application file.
- **The New Source Review list** had 296 rows in three groups: 254 case-by-case permits, 37 concrete batch plant standard permits and 5 standard permits. Received dates run from June 18, 2023 to September 25, 2026. Most rows also link a plain language notice.
- **The Title V list** had 328 rows. Received dates run from December 12, 2011 to November 16, 2026.
- **The link text gives the stage:** "Administrative Complete Application" or "Technically Complete Application".
- **No county, city or address.** A row has to be matched to a place from the application file or from another record.
- **Eight rows name a data center in the applicant or facility column, four on each list.** On the New Source Review list their received dates run from November 2025 to March 2026. On the Title V list they run from July 2025 to August 2026. They are useful cases for the backtest. A search for those two words misses any project filed under another name.
- **The files send an ETag and a Last-Modified header.**
- The pages wrap long lines. Some link addresses are broken across two lines, and the parser joins them.

## How the collector works

1. It asks for the two pages, each with the ETag of the copy it holds. An unchanged file costs one short answer.
2. It compares the rows and the "Data Updated" date with the last copy. The daily rebuild of the New Source Review page is not stored again.
3. It stops there. Each row links an application file, a PDF. The collector keeps the address and does not fetch the file. The two pages link 624 of them.

It keeps to one request every 5 seconds. If a page stops looking like the saved copies, the run keeps that page, fails and waits for a person.

## Private individuals

- **Two rows on the New Source Review list name a person as the applicant**, not a company. The Title V list had none.
- **The fixture does not carry those names.** The saved copy replaces the two applicant names and one facility name that repeats a surname. Its `.meta.json` records the hash of the page as retrieved and the hash of the saved copy.
- **A real run stores the page as TCEQ publishes it**, in the private archive.
- **Nothing here checks for a person's name yet.** The processing step in M4 has to hold back any row whose applicant is not an organization, before a reviewer or the public sees it. This is open.

## Verified live

- The start page and the two lists, fetched once each on November 20, 2026 through `collectors.capture`. The start page is not committed.
- One dry run of the collector the same day: 2 documents, no errors. A dry run keeps nothing.

## What was not verified

- Why two New Source Review rows show received dates in September 2026, after the "Data Updated" date. The page does not say.
- Whether TCEQ will keep the New Source Review page online, and for how long.
- Whether TCEQ will move the Title V list to the portal.
- Any application file. None was fetched. Their size and whether they hold text or scans are unknown.
- The plain language notice page that the New Source Review rows link to.
- How a row leaves a list: on issuance, on withdrawal or both.
- Older versions of either list. The backtest gets only what the page shows today, plus what the collector saves from now on.
- A run from GitHub's servers.

## Other

- TCEQ offers email updates through GovDelivery. Whether a list covers pending air applications was not checked.
- The governor's September 21, 2026 directive paused permits for data center projects. How that changes what these lists show is unknown.
- The TCEQ privacy policy page was requested and returned nothing relevant to automated access. We did not read it line by line.
- The portal is covered in [tx_tceq_air_pending.md](tx_tceq_air_pending.md).
