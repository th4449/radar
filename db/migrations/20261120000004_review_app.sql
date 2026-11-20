-- Rules the reviewer app rests on. See BUILD_PLAN.md section 7.
--
--   A site is rejected when a rejection stands and no confirmation does. Until now a rejection
--     blocked publication and nothing recorded it on the site.
--   reviewers.application_note   who the applicant says they are, for the organization to weigh.
--   reviewer_directory()         applicants and reviewers with their email, for administrators.
--   merge_sites()                an administrator folds one site into another that is the same
--                                place.

-- A site's status follows its standing reviews ----------------------------------------------------

create function private.refresh_site_status(p_site_id bigint) returns void
  language plpgsql security definer set search_path = ''
as $$
declare
  current_status text;
  next_status    text;
begin
  select status into current_status from public.sites where id = p_site_id for update;
  -- A published site comes down only when its alert does. See private.guard_alerts.
  if current_status is null or current_status = 'confirmed' then
    return;
  end if;
  if private.standing_reviews(p_site_id, 'reject') > 0
     and private.standing_reviews(p_site_id, 'confirm') = 0 then
    next_status := 'rejected';
  elsif exists (select 1 from public.reviews where site_id = p_site_id) then
    next_status := 'in_review';   -- reviewers disagree, are unsure, or a rejection was lifted
  else
    next_status := current_status;
  end if;
  update public.sites set status = next_status
    where id = p_site_id and status <> next_status;
end;
$$;

create function private.site_status_after_review() returns trigger
  language plpgsql security definer set search_path = ''
as $$
begin
  perform private.refresh_site_status(new.site_id);
  return null;
end;
$$;

-- Runs after reviews_b_after, which logs the review and handles a published alert.
create trigger reviews_c_site_status
  after insert or update on public.reviews
  for each row execute function private.site_status_after_review();

-- A suspended reviewer's decisions stop standing, and stand again if they are approved again.
create function private.site_status_after_reviewer_change() returns trigger
  language plpgsql security definer set search_path = ''
as $$
begin
  perform private.refresh_site_status(r.site_id)
  from (select distinct site_id from public.reviews
        where reviewer_id = new.user_id and reversed_at is null) r;
  return null;
end;
$$;

create trigger reviewers_c_site_status
  after update of status on public.reviewers
  for each row when (old.status is distinct from new.status)
  execute function private.site_status_after_reviewer_change();

-- Applying ------------------------------------------------------------------------------------------

alter table public.reviewers
  add column application_note text check (length(application_note) <= 2000);
grant insert (application_note) on public.reviewers to authenticated;

-- The reviewer directory ----------------------------------------------------------------------------
-- The organization approves reviewers, so an administrator has to see who is asking. The email
-- lives in auth.users, which no policy opens. This function is the one narrow way to it.

create function public.reviewer_directory()
  returns table (
    user_id uuid, display_name text, email text, status text, role text,
    applied_at timestamptz, approved_at timestamptz, application_note text
  )
  language plpgsql stable security definer set search_path = ''
as $$
begin
  if not private.is_admin() then
    raise exception 'only an administrator reads the reviewer directory' using errcode = '42501';
  end if;
  return query
    select r.user_id, r.display_name, u.email::text, r.status, r.role,
           r.applied_at, r.approved_at, r.application_note
    from public.reviewers r
    join auth.users u on u.id = r.user_id
    order by r.applied_at desc;
end;
$$;

-- Merging two sites that are one place --------------------------------------------------------------
-- The pipeline never merges sites. It flags them. An administrator decides.

create function public.merge_sites(p_from bigint, p_into bigint, p_note text default null)
  returns void
  language plpgsql security definer set search_path = ''
as $$
declare
  folded public.sites;
  kept   public.sites;
  moved  integer;
begin
  if not private.is_admin() then
    raise exception 'only an administrator merges sites' using errcode = '42501';
  end if;
  if p_from = p_into then
    raise exception 'a site cannot be merged into itself' using errcode = '23514';
  end if;
  select * into folded from public.sites where id = p_from for update;
  select * into kept   from public.sites where id = p_into for update;
  if folded.id is null or kept.id is null then
    raise exception 'no such site' using errcode = '23514';
  end if;
  if folded.county_fips <> kept.county_fips then
    raise exception 'sites in different counties are not merged' using errcode = '23514';
  end if;
  -- A reviewer's decision stays on the site it was made about. So does an alert.
  if exists (select 1 from public.reviews where site_id = p_from)
     or exists (select 1 from public.alerts where site_id = p_from) then
    raise exception 'site % has reviews or an alert. Merge the other way round.', p_from
      using errcode = '23514';
  end if;

  update public.signals
    set site_id = p_into,
        extracted = extracted || jsonb_build_object('site_link', 'joined by an administrator')
    where site_id = p_from;
  get diagnostics moved = row_count;
  delete from public.sites where id = p_from;

  perform private.log_action('site.merged', p_into::text,
    jsonb_build_object('from', p_from, 'from_label', folded.label,
                       'signals_moved', moved, 'note', p_note));
end;
$$;

-- Functions in public can be called by anyone unless that is taken away.
revoke all on function public.reviewer_directory() from public, anon;
revoke all on function public.merge_sites(bigint, bigint, text) from public, anon;
grant execute on function public.reviewer_directory() to authenticated;
grant execute on function public.merge_sites(bigint, bigint, text) to authenticated;
alter default privileges in schema public revoke all on functions from public, anon;
