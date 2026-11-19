-- Data Center Early Warning Radar: tables. See BUILD_PLAN.md section 5.
--
-- Additions to the plan's data model, each needed to enforce section 7 in the database:
--   app_settings                      confirmations_required and the admin approval gate.
--                                     A policy cannot read a YAML file.
--   alerts.approved_by, approved_at   who let the alert go public, and when.
--   reviews.reversed_*                an administrator reverses a decision without erasing it.
--   audit_log.actor_role, detail      which kind of caller acted, and what changed.

create extension if not exists postgis with schema extensions;

-- Helper functions live here. The API does not expose this schema.
create schema if not exists private;

-- sources ----------------------------------------------------------------------------------------
create table public.sources (
  id            bigint generated always as identity primary key,
  slug          text not null unique,          -- the id in config/sources.yaml
  state         text not null check (state in ('TX', 'MI', 'US')),
  name          text not null,
  url           text not null,
  method        text not null check (method in ('http', 'browser', 'manual')),
  cadence       text not null,
  robots_status text not null default 'not_checked'
                check (robots_status in ('not_checked', 'allowed', 'restricted', 'blocked')),
  verified_at   timestamptz,
  -- A source may be automated only after its terms and robots rules were checked.
  constraint sources_automation_needs_verification
    check (method = 'manual' or (verified_at is not null and robots_status = 'allowed'))
);

-- documents --------------------------------------------------------------------------------------
create table public.documents (
  id           bigint generated always as identity primary key,
  source_id    bigint not null references public.sources (id),
  url          text not null,
  retrieved_at timestamptz not null,
  sha256       text not null check (sha256 ~ '^[0-9a-f]{64}$'),
  storage_path text,
  text         text,
  county_fips  text check (county_fips ~ '^\d{5}$'),
  raw_meta     jsonb not null default '{}'::jsonb,
  -- The same bytes from the same source are stored once.
  constraint documents_source_sha256_key unique (source_id, sha256)
);
create index documents_county_fips_idx on public.documents (county_fips);
create index documents_retrieved_at_idx on public.documents (retrieved_at);

-- entities ---------------------------------------------------------------------------------------
-- Companies, LLCs and public bodies. Never private individuals.
create table public.entities (
  id               bigint generated always as identity primary key,
  name             text not null,
  normalized_name  text not null,
  parent_entity_id bigint references public.entities (id),
  registry_ref     text,
  notes            text
);
create index entities_normalized_name_idx on public.entities (normalized_name);
create index entities_parent_entity_id_idx on public.entities (parent_entity_id);

-- sites ------------------------------------------------------------------------------------------
create table public.sites (
  id              bigint generated always as identity primary key,
  state           text not null check (state in ('TX', 'MI')),
  county_fips     text not null check (county_fips ~ '^\d{5}$'),
  geom            extensions.geometry (Geometry, 4326),
  label           text not null,
  first_signal_at timestamptz,
  score           numeric not null default 0,
  status          text not null default 'candidate'
                  check (status in ('candidate', 'in_review', 'confirmed', 'rejected'))
);
create index sites_geom_idx on public.sites using gist (geom);
create index sites_state_county_idx on public.sites (state, county_fips);
create index sites_status_idx on public.sites (status);

-- signals ----------------------------------------------------------------------------------------
-- One dated fact from one document.
create table public.signals (
  id          bigint generated always as identity primary key,
  document_id bigint not null references public.documents (id),
  signal_type text not null,                    -- validated against config/scoring.yaml in code
  event_date  date not null,
  summary     text not null,
  entity_id   bigint references public.entities (id),
  site_id     bigint references public.sites (id),
  confidence  numeric check (confidence between 0 and 1),
  extracted   jsonb not null default '{}'::jsonb -- acres, megawatts, dollars
);
create index signals_document_id_idx on public.signals (document_id);
create index signals_site_id_idx on public.signals (site_id);
create index signals_entity_id_idx on public.signals (entity_id);

-- reviewers --------------------------------------------------------------------------------------
-- Approved by the organization. Anyone may apply. See BUILD_PLAN.md section 7.
create table public.reviewers (
  user_id         uuid primary key references auth.users (id) on delete restrict,
  display_name    text not null check (length(trim(display_name)) between 1 and 120),
  applied_at      timestamptz not null default now(),
  approved_by     uuid references public.reviewers (user_id),
  approved_at     timestamptz,
  agreed_terms_at timestamptz,
  status          text not null default 'pending'
                  check (status in ('pending', 'approved', 'suspended')),
  role            text not null default 'reviewer' check (role in ('reviewer', 'admin'))
);
create index reviewers_approved_by_idx on public.reviewers (approved_by);

-- reviews ----------------------------------------------------------------------------------------
create table public.reviews (
  id             bigint generated always as identity primary key,
  site_id        bigint not null references public.sites (id),
  reviewer_id    uuid not null references public.reviewers (user_id),
  decision       text not null check (decision in ('confirm', 'reject', 'unsure')),
  note           text,
  source_checked boolean not null default false,
  created_at     timestamptz not null default now(),
  reversed_at    timestamptz,
  reversed_by    uuid references public.reviewers (user_id),
  reversal_note  text,
  -- A reviewer confirms or rejects only after opening the archived source and ticking the box.
  constraint reviews_decision_needs_source_check check (decision = 'unsure' or source_checked)
);
-- One standing decision per reviewer per site.
create unique index reviews_one_standing_per_reviewer
  on public.reviews (site_id, reviewer_id) where reversed_at is null;
create index reviews_reviewer_id_idx on public.reviews (reviewer_id);
create index reviews_reversed_by_idx on public.reviews (reversed_by);

-- alerts -----------------------------------------------------------------------------------------
create table public.alerts (
  id                 bigint generated always as identity primary key,
  site_id            bigint not null unique references public.sites (id),
  published_at       timestamptz,
  headline           text not null,
  body               text not null,
  confirmed_by_count integer not null default 0,
  approved_by        uuid references public.reviewers (user_id),
  approved_at        timestamptz,
  created_at         timestamptz not null default now()
);
create index alerts_published_at_idx on public.alerts (published_at);
create index alerts_approved_by_idx on public.alerts (approved_by);

-- subscribers ------------------------------------------------------------------------------------
-- Open to anyone. Signing up for alerts never grants review rights.
create table public.subscribers (
  user_id           uuid primary key references auth.users (id) on delete cascade,
  email             text not null,
  states            text[] not null
                    check (cardinality(states) >= 1 and states <@ array['TX', 'MI']::text[]),
  county_fips       text[],
  frequency         text not null default 'weekly' check (frequency in ('each', 'weekly')),
  confirmed_at      timestamptz,                -- set by a trusted job after double opt in
  unsubscribe_token uuid not null default gen_random_uuid() unique,
  created_at        timestamptz not null default now()
);

-- audit_log --------------------------------------------------------------------------------------
-- Append only. Written by triggers.
create table public.audit_log (
  id         bigint generated always as identity primary key,
  actor      uuid,                              -- null when the owner acted by hand in SQL
  actor_role text,
  action     text not null,
  target     text not null,
  detail     jsonb not null default '{}'::jsonb,
  at         timestamptz not null default now()
);
create index audit_log_at_idx on public.audit_log (at);
create index audit_log_actor_idx on public.audit_log (actor);

-- app_settings -----------------------------------------------------------------------------------
-- One row. Settings the policies depend on.
create table public.app_settings (
  id                     boolean primary key default true check (id),
  confirmations_required integer not null default 1 check (confirmations_required between 1 and 5),
  admin_gate_enabled     boolean not null default true,
  updated_by             uuid references public.reviewers (user_id),
  updated_at             timestamptz not null default now()
);
insert into public.app_settings default values;
