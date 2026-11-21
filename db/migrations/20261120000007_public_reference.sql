-- A public alert names each record by its own number.
--
-- One archived file can hold many records: the state's well report download holds every report.
-- Two signals from it showed the public two identical source lines. Each signal now carries a
-- short reference written by the pipeline, such as a well report's tracking number or a permit
-- number, and the public view passes it on.
--
-- The reference is a record's identifier. It is never a summary and never names a party.
-- Nothing else about the view changes: same columns, same rows, same owner rights.

create or replace view public.public_alerts
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
               'event_date',   sg.event_date,
               'reference',    sg.extracted ->> 'reference')
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
