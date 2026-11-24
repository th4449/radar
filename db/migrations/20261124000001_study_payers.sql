-- The money cross-reference. See BUILD_PLAN.md milestone M12.
--
-- The QPQ Tracker's study of who paid for the data centers lists the payers it counts. The
-- radar keeps that list and notes which companies on record have the same name as a payer.
--
--   study_payers           one row per payer, as the study writes it, with the address of its
--                          page in the study and the stored copy of the page it was read from.
--   entity_study_payers    a company on record whose name is a payer's name, and how they met.
--
-- A match is by name. It says the name is in the study. It says nothing about a site, and it
-- is never proof that two names are one company.
--
-- Both tables are written by the pipeline alone and rebuilt from the newest stored copy of the
-- page. Approved reviewers read them. The public sees one thing: a published alert gives the
-- payer's name as the study writes it and the address of its page. Never the name a record gave.

-- study_payers -------------------------------------------------------------------------------------
create table public.study_payers (
  id          bigint generated always as identity primary key,
  document_id bigint not null references public.documents (id),
  name        text not null check (name <> ''),
  payer_class text not null check (payer_class <> ''),
  -- The only link the public page makes from this table. It can lead nowhere but the study.
  url         text not null check (
                url ~ '^https://www\.purchasingpolicy\.org/entity/[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'
              ),
  states      text[] not null,
  unique (name),
  unique (url)
);
create index study_payers_document_id_idx on public.study_payers (document_id);

-- entity_study_payers ------------------------------------------------------------------------------
create table public.entity_study_payers (
  entity_id    bigint not null references public.entities (id) on delete cascade,
  payer_id     bigint not null references public.study_payers (id) on delete cascade,
  basis        text not null check (basis in ('same_name', 'same_name_legal_form_aside')),
  -- The payer's name or the listed other name that the company's name met.
  matched_name text not null check (matched_name <> ''),
  primary key (entity_id, payer_id)
);
create index entity_study_payers_payer_id_idx on public.entity_study_payers (payer_id);

alter table public.study_payers enable row level security;
alter table public.entity_study_payers enable row level security;

revoke all on public.study_payers, public.entity_study_payers from anon, authenticated, public;
grant all on public.study_payers, public.entity_study_payers to service_role;
grant select on public.study_payers, public.entity_study_payers to authenticated;

create policy "approved reviewers read study payers" on public.study_payers
  for select to authenticated using ((select private.is_approved_reviewer()));
create policy "approved reviewers read study matches" on public.entity_study_payers
  for select to authenticated using ((select private.is_approved_reviewer()));

-- The public view ----------------------------------------------------------------------------------
-- One new column at the end. Everything else is as it was: same rows, same owner rights.
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
  ), '[]'::jsonb)      as sources,
  coalesce((
    select jsonb_agg(jsonb_build_object('name', p.name, 'url', p.url) order by p.name)
    from (
      select distinct sp.name, sp.url
      from public.signals sg
      join public.entity_study_payers m on m.entity_id = sg.entity_id
      join public.study_payers sp on sp.id = m.payer_id
      where sg.site_id = s.id
    ) p
  ), '[]'::jsonb)      as study_payers
from public.alerts a
join public.sites s on s.id = a.site_id
where a.published_at is not null
  and s.status = 'confirmed';

revoke all on public.public_alerts from anon, authenticated, public;
grant select on public.public_alerts to anon, authenticated, service_role;
