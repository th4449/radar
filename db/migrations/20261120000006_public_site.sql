-- Rules the public site and the alert emails rest on. See BUILD_PLAN.md section 7.
--
--   confirm_subscription()   the second half of double opt in. A subscription counts only after
--                            the sign-in service has proved the account's address with an emailed
--                            link, and the person has confirmed.
--   unsubscribe(token)       the link in every email. It works without signing in.
--   subscribers.county_fips  five digit codes, each in a state the person selected.
--   corrections              anyone may send one through submit_correction(). Only an
--                            administrator reads them.
--   alert_sends              which alert went to which subscriber, so nothing is sent twice.
--                            Only the email job touches it.
--   email_runs               a log of every run of the email job. Counts only, never an address.

-- Double opt in -------------------------------------------------------------------------------------
-- The first opt in is the form. The second is the link the sign-in service emails to the address.
-- This function is the only way confirmed_at is ever set for a person, and it checks the proof
-- itself rather than trusting that a signed-in caller must have one.

create function public.confirm_subscription() returns timestamptz
  language plpgsql security definer set search_path = ''
as $$
declare
  actor   uuid := auth.uid();
  address text;
  proved  timestamptz;
  stamp   timestamptz;
begin
  if actor is null then
    raise exception 'sign in to confirm a subscription' using errcode = '42501';
  end if;
  select u.email::text, u.email_confirmed_at into address, proved
    from auth.users u where u.id = actor;
  if address is null or proved is null then
    raise exception 'this address has not been confirmed by an emailed link'
      using errcode = '42501';
  end if;
  -- The address is read from the account again. If it changed, this confirmation is a new one.
  update public.subscribers s
    set confirmed_at = case when s.email = address and s.confirmed_at is not null
                            then s.confirmed_at else now() end,
        email = address
    where s.user_id = actor
    returning s.confirmed_at into stamp;
  return stamp;   -- null when the caller has no subscription
end;
$$;

-- Unsubscribe ---------------------------------------------------------------------------------------
-- The token is a random uuid that only the subscriber's own emails carry. Removing the row
-- removes the address and, through alert_sends, the record of what was sent to it.

create function public.unsubscribe(p_token uuid) returns boolean
  language plpgsql security definer set search_path = ''
as $$
declare
  gone integer;
begin
  if p_token is null then
    return false;
  end if;
  delete from public.subscribers where unsubscribe_token = p_token;
  get diagnostics gone = row_count;
  return gone > 0;
end;
$$;

-- Counties ------------------------------------------------------------------------------------------
-- No list means every county in the selected states. An empty list is refused so that it can
-- never be read as "no counties".

create function private.counties_fit_states(p_states text[], p_counties text[]) returns boolean
  language sql immutable set search_path = ''
as $$
  select p_counties is null or (
    cardinality(p_counties) between 1 and 120
    and not exists (
      select 1 from unnest(p_counties) as c (fips)
      where c.fips is null
         or c.fips !~ '^\d{5}$'
         or not ((left(c.fips, 2) = '48' and 'TX' = any (p_states))
              or (left(c.fips, 2) = '26' and 'MI' = any (p_states)))
    )
  );
$$;
-- A check constraint runs its function as the person writing the row.
grant execute on function private.counties_fit_states(text[], text[]) to authenticated, service_role;

alter table public.subscribers
  add constraint subscribers_counties_fit_states
  check (private.counties_fit_states(states, county_fips));

-- Corrections ---------------------------------------------------------------------------------------

create table public.corrections (
  id           bigint generated always as identity primary key,
  alert_id     bigint references public.alerts (id),
  message      text not null check (length(trim(message)) between 10 and 4000),
  contact      text check (length(contact) <= 200),   -- how to reach the reader, if they gave it
  created_at   timestamptz not null default now(),
  handled_at   timestamptz,
  handled_by   uuid references public.reviewers (user_id),
  handled_note text check (length(handled_note) <= 2000)
);
create index corrections_created_at_idx on public.corrections (created_at desc);
create index corrections_alert_id_idx on public.corrections (alert_id);
create index corrections_handled_by_idx on public.corrections (handled_by);

alter table public.corrections enable row level security;
revoke all on public.corrections from anon, authenticated, public;
grant all on public.corrections to service_role;
grant select on public.corrections to authenticated;
grant update (handled_at, handled_note) on public.corrections to authenticated;

create policy "admins read corrections" on public.corrections
  for select to authenticated using ((select private.is_admin()));
create policy "admins mark corrections handled" on public.corrections
  for update to authenticated
  using ((select private.is_admin()))
  with check ((select private.is_admin()));

-- Who handled it is recorded by the database, never taken from the request.
create function private.guard_corrections() returns trigger
  language plpgsql security invoker set search_path = ''
as $$
begin
  if new.handled_at is distinct from old.handled_at
     or new.handled_note is distinct from old.handled_note then
    new.handled_by := case when new.handled_at is null then null else auth.uid() end;
  end if;
  return new;
end;
$$;
create trigger corrections_a_guard
  before update on public.corrections
  for each row execute function private.guard_corrections();

-- The log says that a correction was handled and by whom. It never copies the reader's words or
-- contact.
create function private.audit_corrections() returns trigger
  language plpgsql security definer set search_path = ''
as $$
begin
  if new.handled_at is distinct from old.handled_at then
    perform private.log_action(
      case when new.handled_at is null then 'correction.reopened' else 'correction.handled' end,
      'corrections:' || new.id,
      jsonb_build_object('alert_id', new.alert_id));
  end if;
  return null;
end;
$$;
create trigger corrections_b_audit
  after update on public.corrections
  for each row execute function private.audit_corrections();

-- The one way in for a reader. The form needs no account, so the limits are here.
create function public.submit_correction(
  p_message text, p_alert_id bigint default null, p_contact text default null
) returns void
  language plpgsql security definer set search_path = ''
as $$
declare
  recent integer;
begin
  -- A crude brake, since the database cannot tell one anonymous sender from another.
  select count(*) into recent from public.corrections
    where created_at > now() - interval '1 hour';
  if recent >= 30 then
    raise exception 'too many corrections in the last hour. Try again later.'
      using errcode = '23514';
  end if;
  -- Only an alert the public can see. Anything else would reveal which drafts exist.
  if p_alert_id is not null and not exists (
       select 1 from public.public_alerts where alert_id = p_alert_id) then
    raise exception 'no such public alert' using errcode = '23514';
  end if;
  insert into public.corrections (alert_id, message, contact)
    values (p_alert_id, trim(p_message), nullif(trim(p_contact), ''));
end;
$$;

-- The send ledger -----------------------------------------------------------------------------------

create table public.alert_sends (
  id       bigint generated always as identity primary key,
  user_id  uuid not null references public.subscribers (user_id) on delete cascade,
  alert_id bigint not null references public.alerts (id),
  kind     text not null check (kind in ('each', 'weekly')),
  sent_at  timestamptz not null default now(),
  -- One alert reaches one person once, whichever kind of email carried it.
  constraint alert_sends_once unique (user_id, alert_id)
);
create index alert_sends_alert_id_idx on public.alert_sends (alert_id);

alter table public.alert_sends enable row level security;
revoke all on public.alert_sends from anon, authenticated, public;
grant all on public.alert_sends to service_role;
grant usage on sequence public.alert_sends_id_seq to service_role;

-- The email run log ---------------------------------------------------------------------------------

create table public.email_runs (
  id          bigint generated always as identity primary key,
  started_at  timestamptz not null default now(),
  finished_at timestamptz,
  kind        text not null check (kind in ('each', 'weekly')),
  dry_run     boolean not null,
  status      text not null default 'running' check (status in ('running', 'ok', 'failed')),
  alerts      integer not null default 0,   -- alerts that were due to someone
  recipients  integer not null default 0,   -- people with at least one message
  messages    integer not null default 0,   -- messages sent, or that would have been
  held_over   integer not null default 0,   -- messages left for the next run by the daily limit
  detail      jsonb not null default '{}'::jsonb,
  error       text
);
create index email_runs_started_idx on public.email_runs (started_at desc);

alter table public.email_runs enable row level security;
revoke all on public.email_runs from anon, authenticated, public;
grant all on public.email_runs to service_role;
grant usage on sequence public.email_runs_id_seq to service_role;
grant select on public.email_runs to authenticated;

create policy "admins read email runs" on public.email_runs
  for select to authenticated using ((select private.is_admin()));

-- Who may call what ---------------------------------------------------------------------------------
-- Functions in public can be called by anyone unless that is taken away.

revoke all on function public.confirm_subscription() from public, anon;
revoke all on function public.unsubscribe(uuid) from public;
revoke all on function public.submit_correction(text, bigint, text) from public;
grant execute on function public.confirm_subscription() to authenticated;
grant execute on function public.unsubscribe(uuid) to anon, authenticated;
grant execute on function public.submit_correction(text, bigint, text) to anon, authenticated;
