# Data Center Early Warning Radar — build plan for Claude Code

Owner — Anti-Corruption Action and Dekleptocracy Alliance. Written November 19, 2026.
Companion document — Data_Center_Early_Warning_Radar_signals_and_free_data.docx (research, sources, costs).

## 1. What we are building

A public early warning system that tells communities a data center may be coming before it is announced. Scheduled collectors pull public records. A pipeline turns them into dated signals tied to a site. A scoring engine flags clusters. Reviewers approved by the organization confirm each alert against the source record. Confirmed alerts appear on a public map and go by email to everyone who signed up for that state.

No single record proves a data center is coming. The product is the cluster, the human check and the link back to the source.

## 2. Decisions already made

- Scope one — a Texas test of 30 counties, listed in section 10.
- Scope two — Michigan statewide. Its four statewide feeds are built in parallel with Texas. Michigan local agendas wait until the Texas backtest sets scoring thresholds.
- The map is public.
- Reviewers are approved by the organization. A person can apply, and only an administrator can grant the reviewer role. See section 7.
- Dekleptocracy Alliance is the administrator. It approves reviewers and approves each alert during the first 30 days.
- Anyone can sign up for the app and receives alerts for the states they select.
- Collector code lives in a public GitHub repository. Never commit secrets, reviewer data or subscriber data.
- Budget target — hosting under 60 dollars a month for the Texas test.

## 3. Stack

- Collectors — Python 3.12, httpx, selectolax or BeautifulSoup, pdfplumber, Playwright only for sites that need JavaScript.
- Scheduling — GitHub Actions cron on standard runners (free for public repositories, see https://docs.github.com/en/billing/concepts/product-billing/github-actions).
- Database — Supabase Postgres with PostGIS, Supabase Auth for reviewers, row level security on every table (pricing at https://supabase.com/pricing).
- Public site and reviewer app — one static front end (Astro or Vite) with MapLibre and supabase-js, hosted on Cloudflare Pages (https://developers.cloudflare.com/pages/functions/pricing/). Map tiles from OpenFreeMap (https://openfreemap.org/).
- Geocoding — Census geocoder, no key needed (https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html).
- Email — Resend (https://resend.com/pricing). Free tier is 3,000 a month and 100 a day. Open signup by state will outgrow the free tier, so plan for the 20 dollar tier and build sending in batches.
- Optional language model triage — Anthropic API, model claude-haiku-5-5, behind a monthly spend cap set in an environment variable (pricing at https://platform.claude.com/docs/en/about-claude/pricing). The system must work with this module switched off.

## 4. Repository layout

```
radar/
  CLAUDE.md                 conventions for future sessions
  BUILD_PLAN.md             this file
  config/
    sources.yaml            one entry per feed (see section 6)
    counties_tx.yaml        the 30 Texas counties
    counties_mi.yaml        Michigan counties and agenda priority
    keywords.yaml           code words and data center terms
    scoring.yaml            points, decay and thresholds
  collectors/
    base.py                 fetch, robots check, rate limit, archive
    tx/  mi/                one module per source
  pipeline/                 extract, classify, entities, geocode, score
  db/migrations/            SQL migrations, RLS policies
  web/                      public site and reviewer app
  backtest/                 harness and report
  tests/fixtures/           saved copies of real source pages
  docs/sources/             one note per source with what was verified
  .github/workflows/        cron jobs and CI
```

## 5. Data model

- sources — id, state, name, url, method (http, browser, manual), cadence, robots_status, verified_at.
- documents — id, source_id, url, retrieved_at, sha256, storage_path, text, county_fips, raw_meta.
- signals — id, document_id, signal_type, event_date, summary, entity_id, site_id, confidence, extracted jsonb (acres, megawatts, dollars).
- entities — id, name, normalized_name, parent_entity_id, registry_ref, notes.
- sites — id, state, county_fips, geom, label, first_signal_at, score, status (candidate, in_review, confirmed, rejected).
- reviews — id, site_id, reviewer_id, decision (confirm, reject, unsure), note, source_checked boolean, created_at.
- alerts — id, site_id, published_at, headline, body, confirmed_by_count.
- reviewers — user id, display name, applied_at, approved_by, approved_at, agreed_terms_at, status (pending, approved, suspended), role (reviewer, admin).
- subscribers — user id, email, states list, optional county_fips list, frequency (each alert or weekly digest), confirmed_at, unsubscribe_token.
- audit_log — actor, action, target, at.

Public reads go through a view of confirmed alerts and their source links only. Nothing else is readable with the anonymous key.

## 6. Sources

Record every feed in config/sources.yaml. Before writing a collector, open the source, read its terms of use and robots rules and write what you found in docs/sources. If a source bars automated access, set method to manual and stop. Do not work around blocks, captchas or logins.

Texas, all statewide and filtered to the 30 counties after collection.

| Feed | Start here | Status |
|---|---|---|
| Newspaper public notices, including 30 day tax abatement notices | www.texaspublicnotices.com, background at https://www.texaspress.com/node/14184 and https://comptroller.texas.gov/economy/development/prop-tax/ch312/abatement-process.php | terms not yet read, alert feature untested |
| TCEQ pending air permit applications | https://www.tceq.texas.gov/permitting/air/airpermit-applications-notices and the TCEQ Permit Search Portal at permit-search.tceq.texas.gov | portal needs a browser, untested |
| TCEQ construction stormwater notices of intent | water quality general permit search described in https://cdn.fs.pathlms.com/1dL9jIAmRK2KniXfbkzs?dl=true | blocked our automated reader, treat as manual until terms are checked |
| ERCOT Regional Planning Group project files | example file https://www.ercot.com/files/docs/2026/07/17/6.-StatusUpdate_Combined_CPS-Energy-Large-Load-Additions-Project-and-STEC-Medina-County-Large-Load-Project_July2026_RPG.pdf | find the index page |
| ERCOT large load reports (aggregate only) | example https://www.ercot.com/files/docs/2026/03/12/March-TAC-Report.pdf and survey update https://www.ercot.com/files/docs/2026/11/05/Community-Impact-RFI-PUC-Update.pdf | context layer, not site level |
| PUC Interchange filings for transmission certificates | interchange.puc.texas.gov, example https://interchange.puc.texas.gov/Documents/55999_42_1397539.PDF | search method to be worked out |
| TWDB well reports | https://www.twdb.texas.gov/groundwater/data/drillersdb.asp and https://www.twdb.texas.gov/groundwater/data/locwwrep.asp | downloadable |
| Comptroller registered data centers | https://comptroller.texas.gov/taxes/data-centers/data-center-lists.php | no county field |
| Comptroller local development agreements | https://comptroller.texas.gov/economy/development/search-tools/sb1340/ | lagging |
| Entity lookup | https://mycpa.cpa.state.tx.us/coa/detailpagehelp.jsp | read terms before automating |
| City and county agendas | civic-scraper, see https://rjionline.org/news/welcome-to-agenda-watch/ | inventory needed, milestone 8 |

Michigan statewide feeds.

| Feed | Start here | Status |
|---|---|---|
| Public Service Commission dockets and orders | news releases such as https://www.michigan.gov/mpsc/commission/news-releases/2025/12/18/mpsc-approves-dte-electric-energy-contracts-for-data-center and https://www.michigan.gov/mpsc/commission/news-releases/2026/10/01/mpsc-approves-dte-electric-google-data-center-and-contracts-protects-customers-from-project-cost, docket list at https://earthjustice.org/experts/shannon-fisk/michigans-public-service-commission-grapples-with-ai-data-center-load | locate the e-dockets search and verify |
| EGLE air permits pending decision | https://www.deq.state.mi.us/aps/downloads/permits/PubNotice/NSR_PTIs_Pending_Decision.pdf | PDF, parse it |
| EGLE notices and permit records | https://www.michigan.gov/egle/maps-data/mienviroportal and the public notice calendar named in https://www.michigan.gov/egle/faqs/environmental-assistance/data-centers | search untested |
| Michigan Strategic Fund board packets and data center certificates | https://www.michiganbusiness.org/services/data-center/ | find the board meeting archive |
| Newspaper zoning hearing notices (15 day rule, https://zeus-milenia.legislature.mi.gov/documents/mcl/pdf/mcl-125-3103.pdf) | no statewide site confirmed yet | verify first |

Baselines for both states — FracTracker (https://www.fractracker.org/data-centers), More Than Just Parks (https://morethanjustparks.com/data-center-tracker/press), WKAR moratorium tracker (https://www.wkar.org/wkar-news/2026-02-27/michigan-data-center-tracker-moratoria-legislation-and-grid-impact), Michigan Advance weekly roundup (https://michiganadvance.com/?p=108625), archived transmission lines (https://www.datalumos.org/datalumos/project/240591/version/V1/view), Texas parcels for the 30 counties (https://www.geographic.texas.gov/stratmap/land-parcels.html).

Keyword list starts from the code words in https://www.tomsguide.com/ai/7-code-words-that-could-mean-an-ai-data-center-is-coming-to-your-town — data center, light industrial, data processing, technology campus, Project plus a code name, development agreement, large load, reinvestment zone, special land use.

## 7. Reviewers and subscribers

Two separate roles. Signing up for alerts never grants review rights.

Reviewers, approved by the organization.

- Anyone may apply to review. An application creates a reviewer row with status pending and no review rights.
- Administrator accounts belong to Dekleptocracy Alliance staff only. The owner creates the first one by hand outside the repository. There is no self-service path to the admin role.
- Only an administrator can set status to approved. Enforce this in a database policy and test it, including a test that a user cannot approve themselves.
- An approved reviewer confirms or rejects a site after opening the archived source and ticking that they did. The number of confirmations needed is a config value, confirmations_required, with a default of 1. The owner can raise it to 2.
- Reviewers cannot edit documents, signals or scores. They can add a note.
- Every action goes in the audit log. An administrator can suspend a reviewer and reverse that reviewer's decisions.
- For the first 30 days after launch an administrator approves each alert before it goes public, then that gate can be lifted by a config change.

Subscribers, open to anyone.

- Anyone can create an account, pick one or more states and receive alerts for those states. Texas and Michigan are the choices at launch.
- Double opt in before any alert is sent. Every email carries an unsubscribe link and the organization's postal address.
- A subscriber may narrow to counties and may choose each alert or a weekly digest. The default is the weekly digest for each selected state.
- Only confirmed alerts are emailed. Each email links to the alert page with its sources.
- Subscriber emails are private. They are never readable with the anonymous key and never leave the database except to the email provider.

Every public alert carries its source links, the date and the word confirmed. There is a visible corrections link.

## 8. Scoring

Config driven in scoring.yaml. Each signal type has points and a half life. A site gets a bonus when two or more independent signal types land within 12 months. Starting weights are placeholders — abatement notice, air permit, transmission filing and commission docket high, well report and stormwater notice medium, entity land purchase and keyword-only agenda hit low. The backtest in milestone 9 sets the real thresholds.

## 9. Milestones

Each milestone ends with passing tests and a short note in docs/progress.md. Collector tests run against saved fixtures, never the live site.

- M0 Scaffold. Repository, CLAUDE.md, config files, migrations for section 5, RLS policies, CI with lint and tests. Done when CI is green and migrations apply to a local Postgres.
- M1 Core library. Fetcher with robots check, rate limit and retry, archive with sha256, text extraction for HTML and PDF, a run log table. Done when a sample collector archives a fixture end to end.
- M2 Texas statewide collectors. One at a time in the table order above. Done when each has a source note, fixtures, tests and a workflow file.
- M3 Michigan statewide collectors. Same standard. Can run in parallel with M2 in a separate worktree.
- M4 Processing. Keyword rules, extraction of company, acres, megawatts and dollars, entity normalization, geocoding and county assignment, optional model triage with spend cap.
- M5 Scoring and site clustering. Unit tests with synthetic signals that cover decay and the multi-signal bonus.
- M6 Reviewer app. Reviewer application form, administrator approval screen, review queue, the rules in section 7. Tests for every RLS policy, including a pending reviewer trying to confirm an alert and a user trying to approve themselves.
- M7 Public site and alerts. Map, state and county pages, alert pages with sources, methodology, corrections form, account signup with state selection and double opt in, alert email job by state in dry run mode with each alert and weekly digest options.
- M8 Texas agendas. First produce an inventory CSV of every commissioners court, city council, planning body and development corporation in the 30 counties with the platform each uses. Then build collectors in three batches of ten counties.
- M9 Backtest. For each known project in the 30 counties, find when each signal first appeared and compare with the date it became public. Output a report with hit rate, misses, false alarms in the control counties and median lead time. Propose thresholds.
- M10 Launch. Checklist, monitoring for failed collectors, admin runbook.
- M11 Michigan agendas. Washtenaw, Wayne, Oakland, Monroe, Allegan and Kalamazoo first.
- M12 Money cross-reference. Match resolved parent companies to the payer list in the QPQ Tracker study (https://www.purchasingpolicy.org/data-centers) through its API (https://www.purchasingpolicy.org/api-docs, untested). Show on each alert whether the company appears in that study.

## 10. Texas counties

config/counties_tx.yaml holds 30 counties.

- 25 from the organization's ranking of documented data center conflict — Hood, Hill, Potter, Archer, Somervell, Henderson, Austin, Tom Green, Lubbock, Parker, Wise, Erath, Bosque, Johnson, Ellis, Carson, Callahan, San Saba, Burnet, Milam, Freestone, Falls, Matagorda, Hopkins and Bowie.
- 5 with the most data center activity that were not already in the set — Dallas, Taylor, Bexar, Travis and Harris. This ranking is by facility count (operating, under construction, planned and proposed) from one commercial tracker, https://www.electricchoice.com/datacenters/texas/, read November 19, 2026. Other trackers rank by other measures and differ.

In M0, load the FracTracker baseline and count facilities by county. If its top five outside the 25 differs from the five above, report the difference and wait. Do not change the list without approval.

The five added counties are large urban counties with many cities. Expect the agenda inventory in M8 to be much larger for them than for the rural counties, and size the batches from the inventory, not from the county count.

## 11. Stop and ask before any of these

- Creating or upgrading any paid resource, including a Supabase project.
- Handling secrets. Ask the owner to add them as GitHub and Supabase secrets.
- Sending real email or switching the email job out of dry run.
- Making the site public or lifting the admin approval gate.
- Approving, suspending or removing a reviewer. That is always the owner's action and is never automated.
- Automating any source whose terms or robots rules restrict it.
- Changing the Texas county list or changing scoring thresholds after the backtest.
- Buying a domain or changing DNS.

## 12. Standing rules

- Public records only. Store the URL, retrieval time and hash for everything.
- Be a polite client. Identify the collector in the user agent with a contact address, keep request rates low and cache.
- Never state that a data center is planned unless a source says so. Use the language of signals.
- Do not publish names of private individuals. Companies, LLCs and public officials acting in office are in scope.
- Write tests first for RLS and scoring.
- Small commits with clear messages. Update docs/progress.md at the end of every session.
