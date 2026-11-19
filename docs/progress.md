# Progress

Newest first. Each entry says what was built, what was verified live and what is still unverified.

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

- CI on GitHub. The repository has not been pushed.
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

**Texas county recount: differs from the plan, waiting on the owner**

FracTracker's top five counties outside the organization's 25 are Dallas (27), Bexar (26), Williamson (13), Collin (11) and Tarrant (9). The plan's five are Dallas, Taylor, Bexar, Travis and Harris. In FracTracker, Travis has 6, Harris 3 and Taylor 1. `config/counties_tx.yaml` was not changed. Details and caveats are in the source note.

**Still unverified**

- CI has not run on GitHub. The repository has not been pushed.
- The terms of every source in section 6 except FracTracker.
- Esri's terms for the ArcGIS host that serves the FracTracker layer.
- Whether the hosted Supabase project behaves like the local one for default privileges. The migrations revoke and grant explicitly so it should not matter.

**Open decisions for later milestones**

- M9 names control counties, and the 30-county set has none.
- The subscriber confirmation step (who sets `confirmed_at`) and the unsubscribe-by-token call are M7 work. Today no user can set `confirmed_at`.
- The local database uses ports 55320 to 55329 so it can run beside another Supabase project.
