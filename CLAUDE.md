# Conventions for this repository

Read BUILD_PLAN.md first. It is the specification. If part of it looks wrong, say so and explain before changing course.

## What this is

A public tool that names companies and tells communities a data center may be coming. People act on it. Accuracy and traceability matter more than speed or coverage.

## Hard rules

- This repository is public. Never commit keys, tokens, reviewer data or subscriber emails. When a secret is needed, stop and ask the owner to add it as a GitHub or Supabase secret.
- Stop and ask before anything in BUILD_PLAN.md section 11. That includes paid resources, real email, making the site public, lifting the admin gate, any reviewer approval, the Texas county list and scoring thresholds after the backtest.
- A research pass handed to a subagent carries the same rules as a collector. Tell it so in its brief: a plain connection only and never a stealth proxy, stay off every host marked restricted in `config/tx_agenda_platforms.csv` and `config/sources.yaml`, stop at a 403 or 429, and do not open FracTracker's map or its service. On November 22, 2026 a brief left this out and six pages were read against a block.
- A research pass also checks each host's robots file before the first read, and a second read by a separate pass follows. A site is closed when its file bars every program, bars an AI reader that acts for a user under any name, or does not answer 200 or 404. Never switch tools to get past it, and never open a reprint of a closed paper's story. On November 22, 2026 the trial skipped the robots check and 13 cited lines had to be set aside.
- Before writing a collector, open the source, read its terms of use and robots rules and write a note in `docs/sources/<source-id>.md`. If the source restricts automated access, set `method: manual` in `config/sources.yaml`, tell the owner and move on. Never work around a block, a captcha or a login.
- A source with `verified_at: null` in `config/sources.yaml` must not be fetched by a scheduled job.
- Collector tests use fixtures in `tests/fixtures`. Tests never touch a live site.
- Live requests are slow and identify the collector in the user agent with the contact address from the `RADAR_CONTACT` setting.
- Never state that a data center is planned unless a source says so. Write "signal", not "plan".
- Do not publish names of private individuals. Companies, LLCs and public officials acting in office are in scope.

## Layout

- `config/` YAML that drives everything. `pipeline/config.py` validates it and `tests/test_config.py` checks the files.
- `collectors/` one module per source under `tx/` and `mi/`. Shared fetch and archive code is in `collectors/base.py`.
- `pipeline/` extract, classify, entities, geocode, score. `signals.py` turns one stored document into draft signals and touches no database. `process.py` runs it over the database. `triage.py` is the optional model step, off by default. `alert_email.py` works out the alert emails that are due. It only does dry runs, and a dry run prints no address and no unsubscribe token.
- `web/` the public site and the reviewer desk. Astro, with Preact for the screens that read data. A static build: every page reads the database in the browser with the visitor's own session, so the policies decide what anyone sees. Never put a rule only in the front end. See `web/README.md`.
- `config/tx_agenda_inventory.csv` every commissioners court, city council, planning body and development corporation in the 30 counties, with its agenda page and platform. `pipeline/agenda_inventory.py` loads it and refuses a row that names a platform its own addresses do not show. Research, not a collector.
- `config/tx_agenda_checks.csv` independent second reads of the inventory's pages. `pipeline/agenda_checks.py` gives every row a verdict. **An agenda collector takes a row only if `collectable()` says so,** which means an independent check confirmed it within the last 180 days. A check records what was on the page and never names a platform. Never write a row and its confirming check from the same read.
- `config/tx_agenda_platforms.csv` each agenda platform's standing under its vendor's terms and its robots file. A collector reads a platform only when it is `cleared`, which takes a reading with nothing against it and the owner's word. CivicPlus products are restricted by the vendor's terms. A `candidate` is a platform with nothing found against it that the owner has not cleared. Do not clear a platform yourself. A new outside service gets its own name and address pattern in `pipeline/agenda_inventory.py`, not `other`. Before saying a page holds plain links, ask for it with no script: a browser shows a list that a script drew, and the collector would not see it.
- `config/tx_agenda_site_terms.csv` what each government's own site says. A government is read only if its row there is `own_pages_silent` or `no_terms_found`.
- `collectors/tx/agenda_pages.py` reads the agenda pages of governments that post files on their own sites, then their recent agenda files. One source, many sites: a refusal closes that site for the run and is recorded in `config/tx_agenda_site_terms.csv` as `refused`, never retried. It follows a file only on the government's own site or its site builder's file host. Five counties' sites are provided by the Texas Association of Counties (platform `cira_county_site`): three keep agendas in a calendar drawn by a script, and the collector reads that calendar's RSS feed, whose address the page gives, never the page's script calls. A date is read from the page's words before a file's name, and an unsure date is no date: a month and a year give a month, kept as `month`, never a day. A site built and hosted by a vendor whose terms bar a collector is marked `vendor_site` and stays closed: look for the vendor's credit in the footer, not only for a terms page. The summary of an agenda signal never carries a file name or a link's text: both can name a person.
- `pipeline/ocr.py` reads a PDF that has no text at all with Tesseract, a program installed with `brew install tesseract` or `apt-get`, not a Python package. Nothing leaves the machine. Text read this way is marked on the stored document (`raw_meta.ocr`) and on any signal made from it, in the summary too. Without Tesseract a scan is stored unread and nothing fails. Tests that need it skip unless `RADAR_REQUIRE_OCR=1`, which CI sets.
- `collectors/tx/legistar.py` reads agendas through the Legistar Web API and never fetches an agenda file: the hosts that hold them bar robots. An agenda names people, so the source is `personal_rows` and an agenda signal's summary never quotes an item.
- `scripts/dev_seed.py` fills a local database from the test fixtures. It refuses any other database.
- `db/migrations/` SQL migrations named `<UTC timestamp>_<name>.sql`. `supabase/migrations` is a symlink to this folder so the Supabase CLI finds them.
- `tests/db/` policy tests. They run against `supabase db start`.
- `docs/sources/` one note per source. `docs/services/` one note per outside service the site leans on. `docs/progress.md` gets a few lines at the end of every session.

## Public site and alerts

- The anonymous key reads one thing: the view `public_alerts`. Keep it narrow. Its `reference` for each record is a number, never a name or a summary.
- Anything a stranger may write goes through a function with its own limits, as `submit_correction()` and `unsubscribe()` do. Never grant the anonymous key a table.
- A subscriber's address is never shown, logged or printed: not on the administrator desk, not in a run log, not in a dry run's output.
- Only `confirm_subscription()` sets `confirmed_at`. It checks that the sign-in service proved the address.
- The email job sends only through a `Sender` given to it. The command gives it none. Do not add a way to send without the owner's decision (BUILD_PLAN.md section 11).
- After changing `config/counties_*.yaml` or `config/sources.yaml`, run `uv run python scripts/export_web_data.py`.
- Public copy follows the standing rules: the language of signals, short sentences, no boxes and chips.

## Processing

- A record becomes a signal only with a stated reason, and the reason is stored with it. A summary restates the record.
- A record whose named party does not show a company or a public body makes no signal. Count it by its number. Never write its name anywhere: not in a signal, a log or a test.
- A source that is a list naming people has `personal_rows: true` in `config/sources.yaml`. Its documents are stored restricted and a reviewer cannot read them.
- Never send a record that may name a person to an outside service, the geocoder and the model included.
- Bump `RULES_VERSION` in `pipeline/signals.py` when a rule changes. Reading documents again only adds signals.
- The model's answer is stored beside a signal. It never creates, removes or rewrites one.
- `sites.py` groups signals into sites and scores them at the end of every run. A signal already on a site never moves, and a job never merges, splits, confirms or rejects a site. The database refuses a status change from a job other than candidate to in_review.
- `backtest/harness.py` judges known projects against dated signals for milestone M9. It reuses the rules of `cluster.py` and `score.py` and touches no database. A signal counts from the day it could be seen. The words hit, miss and false alarm are defined at the top of the file. The known projects, their public dates and the control counties are the owner's to approve.
- `backtest/known_projects_tx.csv` the backtest's list of known projects, one row per site, with the first news report (the public date, the owner's definition) and the earliest record found. `backtest/projects.py` loads it and refuses a row that breaks a rule. `backtest/known_projects_hosts.csv` holds the robots result for every site a read rests on, and a test refuses a read on a closed site. `backtest/known_projects.md` says how the list was made and what is not verified. Research, not a collector.
- A history run reads older records once, for the backtest: `python -m collectors.run <source> --history-since 2023-01-01`. Legistar, the ERCOT planning group, governments' own agenda pages and the well reports each have the setting, a `history()` class method. It reads only what an everyday run may read, at the same pace, and skips what is stored, so it can be started again. `config/counties_tx_control.yaml` holds the eleven control counties the owner approved. The radar does not watch them. History is kept outside the repository and outside iCloud, in `~/.local/share/radar/backtest/`, with the local database as `DATABASE_URL`. Dump the database before any `supabase db reset`.

## Database

- Every table in `public` has row level security on. A test fails if one does not.
- The anonymous key reads only the view `public_alerts`. Nothing else.
- Section 7 of the build plan is enforced in policies and triggers, not in the front end. Write the test before the policy.
- `reviewers.status` and `reviewers.role` change only through an administrator who is not the target, or by the owner by hand in SQL. The service role cannot approve anyone.
- Settings that policies depend on live in the table `app_settings`, not in YAML.
- Helper functions live in the `private` schema, which the API does not expose.

## Working style

- Python 3.12, managed with uv. `uv run ruff check .`, `uv run ruff format .` and `uv run pytest` must pass before a commit.
- Small commits with clear messages.
- Write tests first for RLS and scoring.
- When a fact about a source, a price or a law matters to a decision, check it. Say plainly what could not be verified.
- Prose is American English with no serial comma. Short and concrete.
