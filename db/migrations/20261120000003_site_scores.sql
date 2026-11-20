-- Site scores, and who may change a site's status. See BUILD_PLAN.md sections 7 and 8.
--
--   sites.score_detail, scored_at   where every point of the score came from, and when it was
--                                   worked out. A reviewer reads it. The public view does not
--                                   carry it.
--
-- A site is confirmed or rejected through review. Until now nothing stopped a job that holds
-- the service key from setting a site's status itself. A job scores sites and moves a
-- candidate into the reviewers' queue. That is all it may do to a status.

alter table public.sites
  add column score_detail jsonb not null default '{}'::jsonb,
  add column scored_at    timestamptz;

create function private.guard_sites() returns trigger
  language plpgsql set search_path = ''
as $$
begin
  -- A change made from inside one of our own triggers, such as a review or a published alert,
  -- is the review process itself. So is the owner acting by hand in SQL.
  if pg_trigger_depth() > 1 or private.is_owner_by_hand() then
    return new;
  end if;

  if tg_op = 'INSERT' then
    if new.status <> 'candidate' then
      raise exception 'a new site starts as a candidate' using errcode = '42501';
    end if;
    return new;
  end if;

  if new.status is distinct from old.status
     and not (old.status = 'candidate' and new.status = 'in_review') then
    raise exception 'a site is confirmed or rejected through review, not by a job'
      using errcode = '42501';
  end if;
  return new;
end;
$$;

create trigger sites_a_guard
  before insert or update on public.sites
  for each row execute function private.guard_sites();
