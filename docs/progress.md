# Progress

Newest first. Each entry says what was built, what was verified live and what is still unverified.

## November 20, 2026 — M2: TWDB well reports read and held

No code changed. No collector is written for this feed.

**Verified live**

- The download page was fetched once. The bulk file was downloaded once by hand, read and deleted. Its hash is in the source note.
- The file is 145 MB zipped and 823 MB unpacked. The fetcher refuses anything over 50 MB.
- The main table holds 715,155 reports. About 41 percent are household wells with a person's name and address.
- The 30 test counties hold 194,368 reports, 804 of them submitted in the last 30 days.
- Data center operators appear as well owners in 2026 reports, under several kinds of use.
- Reports arrive a median of 36 days after drilling ends.

**Why it is held**

- Built like the other collectors, this feed would download 145 MB a day and archive every copy of a file that names about 293,000 households.
- The source note lists four options. The recommended one is weekly, keeping an extract of non-household rows in the 30 counties and not the file. That departs from the rule that the original is archived, so the owner decides.

**Still unverified**

- The other 21 tables and the 45 MB shapefile.
- Whether a report has a public address a reviewer can open from its tracking number.

**Next in M2**

- Comptroller local agreements. Then M2 is done except for the feeds that are held or closed.

## November 20, 2026 — M2: ERCOT large load reports

**Built**

- `collectors/tx/ercot_large_load.py`: reads the Large Load Working Group and Technical Advisory Committee indexes, the meetings near today and their files. For the committee it fetches only files with "large load" in the title.
- `collectors/tx/ercot_meetings.py`: the ERCOT index and meeting parsers, moved out of the planning group collector so both collectors share them. The planning group collector behaves as before.
- A workflow file, started by hand only, dry run, no schedule.
- `tx_ercot_large_load` is now `method: http`, monthly. Its address is now the working group index.
- 12 new tests. 256 pass locally, database tests included.

**Verified live**

- Six ERCOT pages fetched once each. Four are saved as fixtures.
- One dry run of the collector: 18 documents, no errors.
- **Where the reports are.** The plan had example files and no index. The working group and the committee each have an index page in the planning group's layout.
- **Older planning group meetings.** `/committees/other/rpg/2025` exists, links 14 meetings and links year pages back to 2003. This answers where the backtest finds them.

**Still unverified**

- The committee's November update is a 4.4 MB zip file. It is stored as it comes. Nothing reads inside a zip yet.
- Slide decks and spreadsheets are stored with no text extracted.
- A committee file about large loads whose title lacks those words would be missed.
- The workflow file has never run.

**Next in M2, in the plan's table order**

- TWDB well reports, then Comptroller local agreements.

## November 20, 2026 — M2: TCEQ pending air permit lists

**Built**

- `collectors/tx/tceq_air_pending_legacy.py`: reads TCEQ's two lists of pending air permit applications on its older site. One parser for both.
- It asks for each page with the ETag of the copy it holds and compares rows, so the daily rebuild of one page is not stored again.
- It does not fetch the application files the rows link, 624 of them. It keeps their addresses.
- A workflow file, started by hand only, dry run, no schedule.
- `tx_tceq_air_pending_legacy` is now `method: http`, weekly. It was monthly.
- 19 new tests. 244 pass locally, database tests included.

**Verified live**

- Both lists and the start page fetched once each. The two lists are saved as fixtures.
- One dry run of the collector: 2 documents, no errors.
- **The Title V list is still updated.** Its newest application was received November 16, 2026. The earlier note said both lists stop at August 2026. The start page says that only of New Source Review.
- The New Source Review list shows "Data Updated: 8/28/2026" and 296 rows. The Title V list shows 328.
- Eight rows name a data center, four on each list.
- **Two rows name a person as the applicant.** The fixture replaces those names. Its `.meta.json` says so.

**Still unverified**

- The lists give no county. Matching a row to a place needs the application file or another record.
- No application file was fetched. Their size and form are unknown.
- Why two New Source Review rows carry September 2026 dates, after the "Data Updated" date.
- How long TCEQ keeps the New Source Review page online.
- The workflow file has never run.

**Open for M4**

- A row whose applicant is a person must be held back before a reviewer or the public sees it. Nothing checks for that yet.

**Next in M2, in the plan's table order**

- ERCOT large load reports, then TWDB well reports and Comptroller local agreements.

## November 19, 2026 — M2 started: ERCOT planning group collector

**Built**

- `collectors/tx/ercot_rpg.py`: reads the planning group index, the meetings near today and the files those meetings list. Parsers for the index and for a meeting page.
- The collector base class can now follow links from a page, ask for a file it already holds with its ETag, and skip a page whose content did not change. It stops after 500 URLs.
- `collectors/run.py`: one command to run a collector. A dry run keeps nothing. A real run needs a database and an archive folder.
- Workflow files for the two collectors that exist, ERCOT and the Comptroller list. Both start by hand only and run dry. No schedule.
- `tx_ercot_rpg` is now `method: http`.
- 30 new tests. 225 pass locally, database tests included.

**Verified live**

- Three ERCOT pages saved as fixtures: the index and two meeting pages.
- One ERCOT file fetched by hand to check its headers and text. It is 1.6 MB, so it is not committed. Its hash is in the source note.
- One dry run of the whole collector against ERCOT: 13 documents, no errors.
- ERCOT's pages change a few bytes on every request. The collector compares content, not bytes.

**Still unverified**

- The workflow files have never run. The repository variable `RADAR_CONTACT` is not set, so a run started now would refuse to fetch.
- A run from GitHub's servers. ERCOT's site sits behind a screening service.
- Where ERCOT lists meetings before 2026. The backtest needs them.
- Extraction of company, megawatts and county from the files. That is M4.

**Next in M2, in the plan's table order**

- TCEQ legacy pending air lists, then ERCOT large load reports, TWDB well reports and Comptroller local agreements.
- Held or closed: newspaper public notices, PUC Interchange, TCEQ stormwater. The TCEQ portal waits on the owner's choice of method.

## November 19, 2026 — TCEQ portal read, EGLE contacts found

No code changed. This entry covers source checks and letters.

**Verified live**

- **TCEQ Permit Search Portal, read in a browser.** No login, no terms of its own and no robots rules. Its footer links to the TCEQ web policies, which call site content public domain. Nothing read restricts automated access. `tx_tceq_air_pending` now has its own note and is marked verified. It stays manual.
- **How the portal search works.** A circle around a point, 1 to 60 miles, with filters for status and permit type and no date filter. One search was run, for Hood County. The data comes from three POST calls on the same host.
- **EGLE contacts.** The MiEnviro Portal contact page gives one address for air, one for water and a general help desk. They are in the two EGLE notes.
- **MiEnviro Portal.** Its public notice search needs no account. Alerts on new notices need one. Read from search results only. Nothing was requested from the portal.
- The pending air permit lists moved to `egle.state.mi.us`. The config has the new address.

**Still unverified**

- The bodies of the portal's data calls, its page size and whether any record carries a received date.
- Whether the Michigan.gov terms cover `egle.state.mi.us`, and which office can grant a written agreement.

**Needs the owner**

- A method for the TCEQ portal: the page's own search calls or a browser. The collector base class makes GET requests only, so either choice needs new code.
- Four requests are drafted and not sent: Texas Press Association, Texas PUC and two to EGLE. They are in `drafts/permission-requests.md`, which is not committed.

## November 19, 2026 — M1 closed: first real collector

The owner chose the public contact address for the user agent. That unblocked the last M1 step.

**Built**

- `tests/fixtures/tx_comptroller_data_centers/`: a saved copy of the Comptroller's registered data center page with its URL, retrieval time and hash.
- `collectors/tx/comptroller_data_centers.py`: the collector for that page and a parser for its two tables. 70 qualifying data centers and 113 qualifying large data center projects.
- 11 tests. The collector fetches through the real robots pattern, archives the page under its hash, logs the run and finds nothing new on a second run. A changed layout stops the parser.
- `tx_comptroller_data_centers` is now `method: http` in `config/sources.yaml`. It is the first feed cleared for automatic fetching. Nothing is scheduled yet.

**Verified live**

- One request to the Comptroller's page through `collectors.capture`, with the contact address in the user agent. The robots check passed and the page answered 200.
- The page has no county or address column, as the build plan said.
- Every party named on the page is a company.

**Still unverified**

- How often the state updates the page.
- How to place these 183 registrations in a county. The page gives no location, so the baseline layer needs FracTracker or another source for that.
- The run against the hosted database and a hosted archive. Both wait on the Supabase project, which needs the owner's go-ahead.

**Also today**

- The owner sent the request for a written agreement to the Michigan commission. The requests to the Texas Press Association and the Texas PUC are drafted and not sent.
- Counts: 195 tests pass locally.

## November 19, 2026 — Michigan docket site check

The owner asked for a check of the Public Service Commission's E-Dockets site, which is on a separate host from Michigan.gov.

- **Result: restricted. `mi_mpsc_dockets` stays manual.** The robots file allows everything. The site has no terms of its own. Its footer links to the State of Michigan policies page, which bars automated access without a written agreement.
- The feed's address in `config/sources.yaml` now points at the docket site. The note is `docs/sources/mi_mpsc_dockets.md`.
- A person can read the case list by hand. New cases appear sorted by open date, with no account needed.
- The case list shows complaint cases under the names of private households. Those names stay out of fixtures and out of anything we publish.

**Verified live:** the robots file, the home page and the help page of the docket site, and the policies page its footer links to. One request each.

**Still unverified:** whether the State grants written agreements for this use, the sign-up step for filing notices and the archived orders search on a third host.

## November 19, 2026 — Texas source checks ahead of M2

Done while M1 waits on the contact address. Terms of use and robots rules were read for every Texas statewide feed in BUILD_PLAN.md section 6. Each has a note in `docs/sources`. No collector was written and no record page was fetched.

| Feed | Result |
|---|---|
| Newspaper public notices | **Restricted.** Terms forbid automated collection and any database or archive of the content, with liquidated damages. |
| TCEQ pending air permits, portal | Not verified. A JavaScript application with no robots file. Needs a person in a browser. |
| TCEQ pending air permits, static lists to August 2026 | Allowed. Useful for the backtest. |
| TCEQ stormwater notices of intent | **Blocked.** robots.txt closes the whole host. |
| ERCOT planning group files | Allowed. Index page found. |
| ERCOT large load reports | Allowed. No index page found yet. |
| PUC Interchange filings | **Held.** Access is open, but the link policy asks for a permission request before copying content. |
| TWDB well reports | Allowed. One nightly bulk file. The start page moved. |
| Comptroller registered data centers | Allowed. |
| Comptroller local development agreements | Allowed. |
| Comptroller entity lookup | Allowed through the bulk file and the official API. The API needs a key the owner registers for. |

**What this changes**

- The plan's strongest Texas signal, the 30 day abatement notice from the statewide notice site, cannot be collected as planned. The same event appears on commissioners court and city agendas (M8) with a shorter lead time.
- Of the plan's four high-weight Texas signal types, one is open today (ERCOT transmission planning), one is held on a permission question (PUC), one needs a browser check (TCEQ portal) and one is closed (notices).
- The well reports feed is simpler than planned: one file a day, no crawling.

**Also built**

- `collectors/capture.py`, a by-hand tool that saves one real page as a test fixture through the same fetcher and rules as the collectors. 12 tests.

**How the checks were done**

- Two research passes read robots files and policy pages with a user agent that named this project, at most five requests per host. They submitted no forms and stopped at any refusal.
- Every restrictive finding was read a second time, directly: the public notice terms, the TCEQ robots file and the PUC link policy.
- Counts: 184 tests pass locally.

**Still unverified**

- Every item listed under "not verified" in each source note. The main ones: no record page, search result or file has been fetched from any of these sources, and the TCEQ portal's terms are unread.
- Texas parcels and local agendas have not been checked. Agendas are M8.

**Waiting on the owner**

- The contact address for `RADAR_CONTACT`.
- Public notices: ask the Texas Press Association for permission, use its email alerts by hand, or rely on agendas.
- PUC Interchange: ask the commission, or decide docket filings fall outside its link policy.
- The three Michigan feeds closed by the state's site terms.
- An API key for the Comptroller, when entity lookup is built in M4.

## November 19, 2026 — Owner decision on the Texas county list

The owner decided to keep the plan's five added counties: Dallas, Taylor, Bexar, Travis and Harris. The FracTracker recount stays on file in `docs/sources/us_fractracker.md` as a second measure. `config/counties_tx.yaml` is unchanged.

## November 19, 2026 — Published, first CI run

- The repository is public at https://github.com/th4449/radar with the owner's approval.
- Commits use the account's GitHub no-reply address. The first two local commits carried a personal address and were rewritten before anything was pushed.
- CI passed on the first run: secret scan clean over the full history, lint clean, all five migrations applied from scratch and 172 tests passed with none skipped.
- The workflow's actions were then moved to their current major versions, because GitHub warned that the older ones target a retired Node.js.

**This closes M0.** M1 still lacks the fixture from a real page, which waits on `RADAR_CONTACT`.

**Reminder.** GitHub disables scheduled workflows in a public repository after 60 days without activity. No scheduled workflow exists yet. M10 monitoring has to watch for this.

## November 19, 2026 — M1 Core library

**Built**

- `collectors/base.py`: the fetcher, the archive and the collector run loop.
  - The fetcher refuses a source with no source note, a restricted source and, unless a person runs it by hand, a manual source.
  - robots.txt is read before every request and again on every host a redirect leads to. An unreadable robots file counts as no. There is no switch to skip the check.
  - One request per host every 5 seconds, longer if robots.txt sets a crawl delay. Retry with backoff on server errors. A 401, 403, 451 or repeated 429 stops the run and is never retried.
  - Conditional requests with ETag and Last-Modified, a 50 MB size cap and a user agent that names the collector and the contact address in `RADAR_CONTACT`.
  - The archive stores each original under its SHA-256 hash with URL and retrieval time. Local disk only for now.
- `pipeline/extract.py`: text from HTML and PDF. The kind is read from the bytes, not the header. A PDF with no text layer is flagged for character recognition, which is M8 work.
- `pipeline/store.py` and the `collector_runs` table: every run is logged with its status, counts and error. Documents are stored once per source and hash.
- A sample collector runs end to end on synthetic fixtures: fetch, archive, extract, store, log.
- 67 new tests. 172 in all. None touches the network.

**Changed from the first draft**

- Python's built-in robots parser ignores wildcards and rule length. It would have allowed paths that the Texas Comptroller's `Disallow: /*/` rule forbids. Replaced with Protego, which follows RFC 9309. Tests cover the Comptroller's pattern.

**Verified live**

- State of Michigan website terms bar automated access without a written agreement. Three Michigan feeds are now marked restricted. See `docs/sources/mi_state_of_michigan_terms.md`. **This needs the owner's decision before M3.**
- Texas Comptroller robots rules allow `/taxes/` and `/economy/`, and the site says its information is public domain. See `docs/sources/tx_comptroller_data_centers.md`.

**Not done: waiting on the owner**

- The sample collector has not run against a saved copy of a real page. That takes one live request to the Comptroller's data center list, and the fetcher will not make it until `RADAR_CONTACT` holds the project's public contact address.

**Still unverified**

- The fetcher against a real server. Every test uses a fake transport.
- The hosted archive backend. It comes with the Supabase project.
- A real PDF from a source. The PDF tests use small files written by the test helper.

## November 19, 2026 — M0 Scaffold

**Built**

- Repository layout from BUILD_PLAN.md section 4, `CLAUDE.md`, MIT license, a `.gitignore` that keeps secrets, dumps and raw archives out.
- Config files with strict validation: 22 feeds in `sources.yaml`, the 30 Texas counties, all 83 Michigan counties, keywords and placeholder scoring. Every feed starts as `method: manual`. The loader refuses to mark a source automated unless it has a verification date and allowed robots status.
- Four migrations for the section 5 tables with PostGIS and row level security on every table.
- 96 policy tests, written before the policies, plus 9 config tests. They cover every rule in section 7.
- CI workflow: secret scan, lint, a fresh migration run and the tests. A skipped database test fails CI.

**Additions to the plan's data model**

- `app_settings` holds `confirmations_required` (default 1) and `admin_gate_enabled` (default on). Policies cannot read YAML.
- `alerts.approved_by` and `approved_at`, `reviews.reversed_at`, `reversed_by` and `reversal_note`, `audit_log.actor_role` and `detail`, `sources.slug`.

**Rules the database enforces beyond the plan's wording**

- The service role cannot approve, suspend or remove a reviewer, cannot write a review and cannot change settings. Approval is never automated.
- Nobody changes their own reviewer status, administrators included. The admin role is granted only by the owner by hand in SQL.
- A standing rejection blocks publication until an administrator reverses it.
- Reversing a confirmation takes a published alert down if it no longer has enough confirmations.
- A subscriber's address is copied from their account, so nobody can subscribe someone else's email. Administrators cannot read subscriber rows.
- The audit log cannot be updated, deleted or truncated.

**Verified live**

- Migrations apply from scratch to the local Supabase Postgres 17 and all 105 tests pass.
- The policy tests fail when a guard is switched off. Checked by disabling the reviewers, alerts and reviews guards and RLS on subscribers, one at a time.
- County FIPS codes come from the Census file `national_county2020.txt`.
- GitHub documents that scheduled workflows can be delayed or dropped under load, and that in a public repository they are disabled after 60 days without repository activity.
- Supabase lists the free plan at 500 MB with a pause after one week idle, and Pro at $25 with extra projects from $10.
- FracTracker's terms and robots rules. See `docs/sources/us_fractracker.md`.

**Texas county recount: differs from the plan. Decided later the same day: keep the plan's five.**

FracTracker's top five counties outside the organization's 25 are Dallas (27), Bexar (26), Williamson (13), Collin (11) and Tarrant (9). The plan's five are Dallas, Taylor, Bexar, Travis and Harris. In FracTracker, Travis has 6, Harris 3 and Taylor 1. `config/counties_tx.yaml` was not changed. Details and caveats are in the source note.

**Still unverified**

- The terms of every source in section 6 except FracTracker.
- Esri's terms for the ArcGIS host that serves the FracTracker layer.
- Whether the hosted Supabase project behaves like the local one for default privileges. The migrations revoke and grant explicitly so it should not matter.

**Open decisions for later milestones**

- M9 names control counties, and the 30-county set has none.
- The subscriber confirmation step (who sets `confirmed_at`) and the unsubscribe-by-token call are M7 work. Today no user can set `confirmed_at`.
- The local database uses ports 55320 to 55329 so it can run beside another Supabase project.
