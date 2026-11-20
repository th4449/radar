-- Processing. See BUILD_PLAN.md milestone M4.
--
-- Additions to the plan's data model, each needed to keep names of private individuals away
-- from reviewers and the public, or to keep one fact from being stored twice:
--   documents.restricted            the document is a list that names people. Administrators only.
--   documents.processed_*           when the rules last read the document, and which rules.
--   signals.fingerprint             the same fact from two copies of a list is one signal.
--   signals.county_fips             where the record says the fact is.
--   entities.kind, match_key        a company or a public body, never a person.
--   processing_runs                 a log of every processing run.

-- documents ----------------------------------------------------------------------------------------
alter table public.documents
  add column restricted        boolean not null default false,
  add column processed_at      timestamptz,
  add column processed_version text;
create index documents_processed_version_idx on public.documents (processed_version);

-- A list of permit applicants or well owners names people. A reviewer does not read it. The
-- reviewer reads the signal made from one row, which the pipeline writes only after checking
-- that the row names a company or a public body.
drop policy "approved reviewers read documents" on public.documents;
create policy "reviewers read open documents, admins read all" on public.documents
  for select to authenticated
  using (
    (select private.is_admin())
    or ((select private.is_approved_reviewer()) and not restricted)
  );

-- signals ------------------------------------------------------------------------------------------
alter table public.signals
  add column fingerprint text check (fingerprint ~ '^[0-9a-f]{64}$'),
  add column county_fips text check (county_fips ~ '^\d{5}$');
create unique index signals_fingerprint_key on public.signals (fingerprint);
create index signals_county_fips_idx on public.signals (county_fips);

-- entities -----------------------------------------------------------------------------------------
-- One row per name as normalized. "Example Data LLC" and "Example Data Inc" are two rows:
-- they can be two companies. match_key, the name without its legal form, is only a hint.
alter table public.entities
  add column match_key text,
  add column kind      text not null check (kind in ('company', 'public_body'));
drop index public.entities_normalized_name_idx;
create unique index entities_normalized_name_key on public.entities (normalized_name);
create index entities_match_key_idx on public.entities (match_key);

-- processing_runs ----------------------------------------------------------------------------------
create table public.processing_runs (
  id            bigint generated always as identity primary key,
  started_at    timestamptz not null default now(),
  finished_at   timestamptz,
  status        text not null default 'running'
                check (status in ('running', 'ok', 'partial', 'failed')),
  rules_version text not null,
  documents     integer not null default 0,
  signals_new   integer not null default 0,
  held_back     integer not null default 0,     -- records set aside because they may name a person
  errors        integer not null default 0,
  error         text,
  runner        text,
  detail        jsonb not null default '{}'::jsonb
);
create index processing_runs_started_idx on public.processing_runs (started_at desc);

alter table public.processing_runs enable row level security;

revoke all on public.processing_runs from anon, authenticated, public;
grant all on public.processing_runs to service_role;
grant select on public.processing_runs to authenticated;

create policy "admins read processing runs" on public.processing_runs
  for select to authenticated using ((select private.is_admin()));
