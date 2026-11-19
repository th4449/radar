-- The only thing the anonymous key can read. See BUILD_PLAN.md section 5.
--
-- The view runs with its owner's rights (security_invoker = false) on purpose. The anon role
-- has no grant and no policy on any table, so a security invoker view would return nothing.
-- This view is the single, narrow opening: published alerts on confirmed sites, the site's
-- place, and a link back to each source record.
--
-- Supabase's linter flags owner-rights views. This one is intended. Keep it narrow:
--   no reviewer names or ids, no subscriber data, no review notes, no scores,
--   no machine-written signal summaries, no unpublished alerts.
-- tests/db/test_policies.py pins the exact column list.

create view public.public_alerts
  with (security_invoker = false, security_barrier = true)
as
select
  a.id                 as alert_id,
  s.id                 as site_id,
  a.headline,
  a.body,
  a.published_at,
  a.confirmed_by_count,
  'confirmed'::text    as status,
  s.state,
  s.county_fips,
  s.label,
  extensions.st_asgeojson(s.geom)::jsonb as geometry,
  coalesce((
    select jsonb_agg(
             jsonb_build_object(
               'url',          d.url,
               'source',       src.name,
               'retrieved_at', d.retrieved_at,
               'sha256',       d.sha256,
               'signal_type',  sg.signal_type,
               'event_date',   sg.event_date)
             order by sg.event_date, sg.id)
    from public.signals sg
    join public.documents d on d.id = sg.document_id
    join public.sources src on src.id = d.source_id
    where sg.site_id = s.id
  ), '[]'::jsonb)      as sources
from public.alerts a
join public.sites s on s.id = a.site_id
where a.published_at is not null
  and s.status = 'confirmed';

revoke all on public.public_alerts from anon, authenticated, public;
grant select on public.public_alerts to anon, authenticated, service_role;
