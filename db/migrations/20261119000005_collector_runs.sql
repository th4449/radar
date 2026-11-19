-- Run log. Every collector run is recorded, success or failure, so a broken collector is
-- noticed within a day. See BUILD_PLAN.md milestones M1 and M10.

create table public.collector_runs (
  id             bigint generated always as identity primary key,
  source_id      bigint not null references public.sources (id),
  started_at     timestamptz not null default now(),
  finished_at    timestamptz,
  status         text not null default 'running'
                 check (status in ('running', 'ok', 'partial', 'failed', 'blocked')),
  documents_seen integer not null default 0,
  documents_new  integer not null default 0,
  errors         integer not null default 0,
  error          text,
  runner         text,                          -- for example the GitHub Actions run id
  detail         jsonb not null default '{}'::jsonb
);
create index collector_runs_source_started_idx
  on public.collector_runs (source_id, started_at desc);

alter table public.collector_runs enable row level security;

revoke all on public.collector_runs from anon, authenticated, public;
grant all on public.collector_runs to service_role;
grant select on public.collector_runs to authenticated;

create policy "admins read collector runs" on public.collector_runs
  for select to authenticated using ((select private.is_admin()));
