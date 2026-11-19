-- Row level security, policies and grants. See BUILD_PLAN.md sections 5 and 7.
--
-- Grants are spelled out so the result does not depend on Supabase's default privileges.
-- Everything is revoked first, then each role gets exactly what it needs.
--   anon           nothing here. It reads the view public_alerts, granted in the next migration.
--   authenticated  what the policies below allow, column by column where that matters.
--   service_role   the pipeline. It bypasses RLS, and the guard triggers still bind it.

alter table public.sources      enable row level security;
alter table public.documents    enable row level security;
alter table public.entities     enable row level security;
alter table public.sites        enable row level security;
alter table public.signals      enable row level security;
alter table public.reviewers    enable row level security;
alter table public.reviews      enable row level security;
alter table public.alerts       enable row level security;
alter table public.subscribers  enable row level security;
alter table public.audit_log    enable row level security;
alter table public.app_settings enable row level security;

revoke all on all tables in schema public from anon, authenticated, public;
revoke all on all sequences in schema public from anon, authenticated, public;
revoke all on all functions in schema private from anon, authenticated, public;

-- Tables created later start locked too.
alter default privileges in schema public revoke all on tables from anon, authenticated, public;
alter default privileges in schema public revoke all on sequences from anon, authenticated, public;
alter default privileges in schema private revoke all on functions from anon, authenticated, public;

-- Callers may run only the three "who is asking" checks, which policies and the invoker-rights
-- guards call as the caller. Everything else in private runs only from inside a trigger.
grant usage on schema private to authenticated, service_role;
grant execute on function private.is_admin(), private.is_approved_reviewer(),
  private.is_owner_by_hand() to authenticated, service_role;

grant all on all tables in schema public to service_role;
grant all on all sequences in schema public to service_role;

-- The record: sources, documents, entities, sites, signals ----------------------------------------
-- Approved reviewers and administrators read. Nobody writes through the app.

grant select on public.sources, public.documents, public.entities, public.sites, public.signals
  to authenticated;

create policy "approved reviewers read sources" on public.sources
  for select to authenticated using ((select private.is_approved_reviewer()));
create policy "approved reviewers read documents" on public.documents
  for select to authenticated using ((select private.is_approved_reviewer()));
create policy "approved reviewers read entities" on public.entities
  for select to authenticated using ((select private.is_approved_reviewer()));
create policy "approved reviewers read sites" on public.sites
  for select to authenticated using ((select private.is_approved_reviewer()));
create policy "approved reviewers read signals" on public.signals
  for select to authenticated using ((select private.is_approved_reviewer()));

-- Reviewers ----------------------------------------------------------------------------------------
-- A user may name only these columns when applying. Status and role take their defaults.

grant select on public.reviewers to authenticated;
grant insert (user_id, display_name, agreed_terms_at) on public.reviewers to authenticated;
grant update (display_name, status) on public.reviewers to authenticated;

create policy "see own reviewer row, admins see all" on public.reviewers
  for select to authenticated
  using (user_id = (select auth.uid()) or (select private.is_admin()));

create policy "anyone may apply for themselves after agreeing to the terms" on public.reviewers
  for insert to authenticated
  with check (user_id = (select auth.uid()) and agreed_terms_at is not null);

-- The guard trigger decides which columns each of these callers may really change.
create policy "update own reviewer row" on public.reviewers
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

create policy "admins update reviewer rows" on public.reviewers
  for update to authenticated
  using ((select private.is_admin()))
  with check ((select private.is_admin()));

-- Reviews ------------------------------------------------------------------------------------------

grant select on public.reviews to authenticated;
grant insert (site_id, reviewer_id, decision, note, source_checked) on public.reviews
  to authenticated;
grant update (reversed_at, reversal_note) on public.reviews to authenticated;
grant usage on sequence public.reviews_id_seq to authenticated;

create policy "approved reviewers read reviews" on public.reviews
  for select to authenticated using ((select private.is_approved_reviewer()));

create policy "approved reviewers review as themselves" on public.reviews
  for insert to authenticated
  with check (reviewer_id = (select auth.uid()) and (select private.is_approved_reviewer()));

create policy "admins reverse reviews" on public.reviews
  for update to authenticated
  using ((select private.is_admin()))
  with check ((select private.is_admin()));

-- Alerts -------------------------------------------------------------------------------------------

grant select on public.alerts to authenticated;
grant insert (site_id, headline, body, published_at) on public.alerts to authenticated;
grant update (headline, body, published_at) on public.alerts to authenticated;
grant usage on sequence public.alerts_id_seq to authenticated;

create policy "approved reviewers read alerts" on public.alerts
  for select to authenticated using ((select private.is_approved_reviewer()));

create policy "admins write alerts" on public.alerts
  for insert to authenticated with check ((select private.is_admin()));

create policy "admins edit alerts" on public.alerts
  for update to authenticated
  using ((select private.is_admin()))
  with check ((select private.is_admin()));

-- Subscribers --------------------------------------------------------------------------------------
-- Each user sees and changes only their own row. Administrators get no access to emails.

grant select, delete on public.subscribers to authenticated;
grant insert (user_id, states, county_fips, frequency) on public.subscribers to authenticated;
grant update (states, county_fips, frequency) on public.subscribers to authenticated;

create policy "subscribers read own row" on public.subscribers
  for select to authenticated using (user_id = (select auth.uid()));
create policy "subscribers create own row" on public.subscribers
  for insert to authenticated with check (user_id = (select auth.uid()));
create policy "subscribers update own row" on public.subscribers
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));
create policy "subscribers delete own row" on public.subscribers
  for delete to authenticated using (user_id = (select auth.uid()));

-- Audit log ----------------------------------------------------------------------------------------

grant select on public.audit_log to authenticated;

create policy "admins read the audit log" on public.audit_log
  for select to authenticated using ((select private.is_admin()));

-- Settings -----------------------------------------------------------------------------------------

grant select on public.app_settings to authenticated;
grant update (confirmations_required, admin_gate_enabled) on public.app_settings to authenticated;

create policy "approved reviewers read settings" on public.app_settings
  for select to authenticated using ((select private.is_approved_reviewer()));

create policy "admins change settings" on public.app_settings
  for update to authenticated
  using ((select private.is_admin()))
  with check ((select private.is_admin()));
