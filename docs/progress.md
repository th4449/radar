# Progress

Newest first. Each entry says what was built, what was verified live and what is still unverified.

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
