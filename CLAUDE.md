# Conventions for this repository

Read BUILD_PLAN.md first. It is the specification. If part of it looks wrong, say so and explain before changing course.

## What this is

A public tool that names companies and tells communities a data center may be coming. People act on it. Accuracy and traceability matter more than speed or coverage.

## Hard rules

- This repository is public. Never commit keys, tokens, reviewer data or subscriber emails. When a secret is needed, stop and ask the owner to add it as a GitHub or Supabase secret.
- Stop and ask before anything in BUILD_PLAN.md section 11. That includes paid resources, real email, making the site public, lifting the admin gate, any reviewer approval, the Texas county list and scoring thresholds after the backtest.
- Before writing a collector, open the source, read its terms of use and robots rules and write a note in `docs/sources/<source-id>.md`. If the source restricts automated access, set `method: manual` in `config/sources.yaml`, tell the owner and move on. Never work around a block, a captcha or a login.
- A source with `verified_at: null` in `config/sources.yaml` must not be fetched by a scheduled job.
- Collector tests use fixtures in `tests/fixtures`. Tests never touch a live site.
- Live requests are slow and identify the collector in the user agent with the contact address from the `RADAR_CONTACT` setting.
- Never state that a data center is planned unless a source says so. Write "signal", not "plan".
- Do not publish names of private individuals. Companies, LLCs and public officials acting in office are in scope.

## Layout

- `config/` YAML that drives everything. `pipeline/config.py` validates it and `tests/test_config.py` checks the files.
- `collectors/` one module per source under `tx/` and `mi/`. Shared fetch and archive code is in `collectors/base.py`.
- `pipeline/` extract, classify, entities, geocode, score. `signals.py` turns one stored document into draft signals and touches no database. `process.py` runs it over the database. `triage.py` is the optional model step, off by default.
- `db/migrations/` SQL migrations named `<UTC timestamp>_<name>.sql`. `supabase/migrations` is a symlink to this folder so the Supabase CLI finds them.
- `tests/db/` policy tests. They run against `supabase db start`.
- `docs/sources/` one note per source. `docs/progress.md` gets a few lines at the end of every session.

## Processing

- A record becomes a signal only with a stated reason, and the reason is stored with it. A summary restates the record.
- A record whose named party does not show a company or a public body makes no signal. Count it by its number. Never write its name anywhere: not in a signal, a log or a test.
- A source that is a list naming people has `personal_rows: true` in `config/sources.yaml`. Its documents are stored restricted and a reviewer cannot read them.
- Never send a record that may name a person to an outside service, the geocoder and the model included.
- Bump `RULES_VERSION` in `pipeline/signals.py` when a rule changes. Reading documents again only adds signals.
- The model's answer is stored beside a signal. It never creates, removes or rewrites one.

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
