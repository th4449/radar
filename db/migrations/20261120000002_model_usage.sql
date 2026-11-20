-- What the optional model triage has spent. See BUILD_PLAN.md section 3.
--
-- The monthly cap is checked against this table before every call, so the cap holds across
-- runs and across machines. One row per call, written whether or not the answer was usable.

create table public.model_usage (
  id            bigint generated always as identity primary key,
  at            timestamptz not null default now(),
  model         text not null,
  purpose       text not null,
  document_id   bigint references public.documents (id),
  input_tokens  integer not null check (input_tokens >= 0),
  output_tokens integer not null check (output_tokens >= 0),
  cost_usd      numeric(12, 6) not null check (cost_usd >= 0),
  outcome       text not null                   -- the answer, or refusal, cut_off or unreadable
);
create index model_usage_at_idx on public.model_usage (at);
create index model_usage_document_id_idx on public.model_usage (document_id);

alter table public.model_usage enable row level security;

revoke all on public.model_usage from anon, authenticated, public;
grant all on public.model_usage to service_role;
grant select on public.model_usage to authenticated;

create policy "admins read model usage" on public.model_usage
  for select to authenticated using ((select private.is_admin()));
