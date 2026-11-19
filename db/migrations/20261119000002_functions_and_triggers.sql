-- Functions and triggers that enforce BUILD_PLAN.md section 7.
--
-- Row level security filters rows for the anon and authenticated roles. It does not protect
-- single columns and it does not bind the service role. The guard triggers below close both
-- gaps: they fire for every caller, including a job that holds the service key.
--
-- Guards raise SQLSTATE 42501 (insufficient privilege) when the caller may not do the thing,
-- and 23514 (check violation) when the thing itself breaks a rule.

-- Who is asking ------------------------------------------------------------------------------------

create function private.is_admin() returns boolean
  language sql stable security definer set search_path = ''
as $$
  select exists (
    select 1 from public.reviewers
    where user_id = (select auth.uid()) and role = 'admin' and status = 'approved'
  );
$$;

-- True for approved reviewers and for administrators, who are approved reviewers too.
create function private.is_approved_reviewer() returns boolean
  language sql stable security definer set search_path = ''
as $$
  select exists (
    select 1 from public.reviewers
    where user_id = (select auth.uid()) and status = 'approved'
  );
$$;

-- True when the database owner is acting by hand in SQL, outside the app. This is how the first
-- administrator is created. SECURITY INVOKER on purpose: inside a SECURITY DEFINER function
-- current_user would be the function owner and this would always be true.
create function private.is_owner_by_hand() returns boolean
  language sql stable security invoker set search_path = ''
as $$
  select current_user in ('postgres', 'supabase_admin');
$$;

-- Audit log ----------------------------------------------------------------------------------------

create function private.log_action(p_action text, p_target text, p_detail jsonb default '{}'::jsonb)
  returns void
  language sql security definer set search_path = ''
as $$
  insert into public.audit_log (actor, actor_role, action, target, detail)
  values (
    (select auth.uid()),
    coalesce(nullif(current_setting('role', true), 'none'), session_user),
    p_action, p_target, coalesce(p_detail, '{}'::jsonb)
  );
$$;

create function private.audit_log_is_append_only() returns trigger
  language plpgsql set search_path = ''
as $$
begin
  raise exception 'audit_log is append only' using errcode = '42501';
end;
$$;

create trigger audit_log_no_update_or_delete
  before update or delete on public.audit_log
  for each row execute function private.audit_log_is_append_only();

create trigger audit_log_no_truncate
  before truncate on public.audit_log
  for each statement execute function private.audit_log_is_append_only();

-- Reviewers ----------------------------------------------------------------------------------------
-- Only an administrator can approve or suspend, never their own row, and never a job.
-- Only the owner by hand can grant or remove the admin role or delete a reviewer.

create function private.guard_reviewers() returns trigger
  language plpgsql security invoker set search_path = ''
as $$
declare
  by_hand boolean := private.is_owner_by_hand();
  actor   uuid    := auth.uid();
begin
  if tg_op = 'DELETE' then
    if not by_hand then
      raise exception 'only the owner can remove a reviewer' using errcode = '42501';
    end if;
    return old;
  end if;

  if tg_op = 'INSERT' then
    if not by_hand then
      -- An application. It starts pending with no rights, whatever the caller sent.
      if new.status <> 'pending' or new.role <> 'reviewer'
         or new.approved_by is not null or new.approved_at is not null then
        raise exception 'an application starts as a pending reviewer' using errcode = '42501';
      end if;
      new.applied_at := now();
    end if;
    return new;
  end if;

  -- UPDATE
  if new.user_id <> old.user_id then
    raise exception 'user_id cannot change' using errcode = '42501';
  end if;

  if new.role <> old.role and not by_hand then
    raise exception 'only the owner can change a role' using errcode = '42501';
  end if;

  if new.status <> old.status then
    if not by_hand then
      if not private.is_admin() then
        raise exception 'only an administrator can change a reviewer''s status'
          using errcode = '42501';
      end if;
      if actor = old.user_id then
        raise exception 'nobody changes their own reviewer status' using errcode = '42501';
      end if;
    end if;
    if new.status = 'approved' then
      new.approved_by := actor;   -- null when the owner acted by hand
      new.approved_at := now();
    end if;
  elsif not by_hand then
    -- Status did not change, so the approval record must not either.
    new.approved_by := old.approved_by;
    new.approved_at := old.approved_at;
  end if;

  if not by_hand then
    new.applied_at := old.applied_at;
  end if;
  return new;
end;
$$;

create trigger reviewers_a_guard
  before insert or update or delete on public.reviewers
  for each row execute function private.guard_reviewers();

create function private.audit_reviewers() returns trigger
  language plpgsql security definer set search_path = ''
as $$
declare
  action text;
begin
  if tg_op = 'INSERT' then
    action := case when new.status = 'pending' and new.role = 'reviewer'
                   then 'reviewer.applied' else 'reviewer.created_by_owner' end;
    perform private.log_action(action, new.user_id::text,
      jsonb_build_object('status', new.status, 'role', new.role));
  elsif tg_op = 'DELETE' then
    perform private.log_action('reviewer.removed', old.user_id::text,
      jsonb_build_object('status', old.status, 'role', old.role));
  else
    action := case
      when new.role <> old.role then 'reviewer.role_changed'
      when new.status <> old.status then 'reviewer.' || case new.status
        when 'approved' then 'approved'
        when 'suspended' then 'suspended'
        else 'set_pending' end
      else 'reviewer.updated' end;
    perform private.log_action(action, new.user_id::text,
      jsonb_build_object('old_status', old.status, 'new_status', new.status,
                         'old_role', old.role, 'new_role', new.role));
  end if;
  return null;
end;
$$;

create trigger reviewers_b_audit
  after insert or update or delete on public.reviewers
  for each row execute function private.audit_reviewers();

-- Reviews ------------------------------------------------------------------------------------------
-- Written only by an approved reviewer acting as themselves. No job and no owner shortcut.
-- After that the only change is an administrator's reversal.

create function private.guard_reviews() returns trigger
  language plpgsql security definer set search_path = ''
as $$
declare
  actor uuid := auth.uid();
begin
  if tg_op = 'DELETE' then
    raise exception 'reviews are never deleted. An administrator reverses them.'
      using errcode = '42501';
  end if;

  if tg_op = 'INSERT' then
    if actor is null or new.reviewer_id <> actor or not private.is_approved_reviewer() then
      raise exception 'only an approved reviewer can review, and only as themselves'
        using errcode = '42501';
    end if;
    new.created_at := now();
    new.reversed_at := null;
    new.reversed_by := null;
    new.reversal_note := null;
    return new;
  end if;

  -- UPDATE: a reversal and nothing else.
  if (new.site_id, new.reviewer_id, new.decision, new.source_checked, new.created_at)
       is distinct from
     (old.site_id, old.reviewer_id, old.decision, old.source_checked, old.created_at)
     or new.note is distinct from old.note then
    raise exception 'a review cannot be edited' using errcode = '42501';
  end if;
  if old.reversed_at is not null then
    raise exception 'this review is already reversed' using errcode = '42501';
  end if;
  if not private.is_admin() then
    raise exception 'only an administrator can reverse a review' using errcode = '42501';
  end if;
  new.reversed_at := now();
  new.reversed_by := actor;
  return new;
end;
$$;

create trigger reviews_a_guard
  before insert or update or delete on public.reviews
  for each row execute function private.guard_reviews();

-- Standing confirmations for a site: confirmed, source checked, not reversed, and from a
-- reviewer who is approved right now.
create function private.standing_reviews(p_site_id bigint, p_decision text) returns integer
  language sql stable security definer set search_path = ''
as $$
  select count(distinct r.reviewer_id)::integer
  from public.reviews r
  join public.reviewers rv on rv.user_id = r.reviewer_id
  where r.site_id = p_site_id
    and r.decision = p_decision
    and r.source_checked
    and r.reversed_at is null
    and rv.status = 'approved';
$$;

create function private.after_review_change() returns trigger
  language plpgsql security definer set search_path = ''
as $$
declare
  required integer;
begin
  if tg_op = 'INSERT' then
    perform private.log_action('review.' || new.decision, new.site_id::text,
      jsonb_build_object('review_id', new.id, 'source_checked', new.source_checked));
    update public.sites set status = 'in_review'
      where id = new.site_id and status = 'candidate';
    return null;
  end if;

  -- A reversal.
  perform private.log_action('review.reversed', new.id::text,
    jsonb_build_object('site_id', new.site_id, 'reviewer_id', new.reviewer_id,
                       'decision', new.decision));
  -- If the site's published alert no longer has the confirmations it needs, take it down.
  select confirmations_required into required from public.app_settings;
  if private.standing_reviews(new.site_id, 'confirm') < required then
    update public.alerts set published_at = null
      where site_id = new.site_id and published_at is not null;
  end if;
  return null;
end;
$$;

create trigger reviews_b_after
  after insert or update on public.reviews
  for each row execute function private.after_review_change();

-- Alerts -------------------------------------------------------------------------------------------
-- An alert goes public only when the site has enough standing confirmations and no standing
-- rejection. While the admin gate is on, only an administrator can publish.

create function private.guard_alerts() returns trigger
  language plpgsql security definer set search_path = ''
as $$
declare
  settings   public.app_settings;
  confirms   integer;
  publishing boolean;
begin
  if tg_op = 'UPDATE' and new.site_id <> old.site_id then
    raise exception 'an alert cannot move to another site' using errcode = '42501';
  end if;

  publishing := new.published_at is not null
                and (tg_op = 'INSERT' or old.published_at is null);

  if publishing then
    select * into settings from public.app_settings;
    confirms := private.standing_reviews(new.site_id, 'confirm');
    if confirms < settings.confirmations_required then
      raise exception 'site % has % of % confirmations needed',
        new.site_id, confirms, settings.confirmations_required using errcode = '23514';
    end if;
    if private.standing_reviews(new.site_id, 'reject') > 0 then
      raise exception 'site % has a standing rejection', new.site_id using errcode = '23514';
    end if;
    if settings.admin_gate_enabled and not private.is_admin() then
      raise exception 'while the approval gate is on, only an administrator can publish'
        using errcode = '42501';
    end if;
    new.published_at := now();
    new.confirmed_by_count := confirms;
    if private.is_admin() then
      new.approved_by := auth.uid();
      new.approved_at := now();
    else
      new.approved_by := null;
      new.approved_at := null;
    end if;
    update public.sites set status = 'confirmed' where id = new.site_id;
  elsif new.published_at is not null then
    -- Already public. The record of how it got there is frozen.
    new.published_at := old.published_at;
    new.confirmed_by_count := old.confirmed_by_count;
    new.approved_by := old.approved_by;
    new.approved_at := old.approved_at;
  else
    -- A draft, or an alert being taken down.
    new.confirmed_by_count := private.standing_reviews(new.site_id, 'confirm');
    new.approved_by := null;
    new.approved_at := null;
    if tg_op = 'UPDATE' and old.published_at is not null then
      update public.sites set status = 'in_review'
        where id = new.site_id and status = 'confirmed';
    end if;
  end if;

  if tg_op = 'INSERT' then
    new.created_at := now();
  else
    new.created_at := old.created_at;
  end if;
  return new;
end;
$$;

create trigger alerts_a_guard
  before insert or update on public.alerts
  for each row execute function private.guard_alerts();

create function private.audit_alerts() returns trigger
  language plpgsql security definer set search_path = ''
as $$
declare
  action text;
begin
  if tg_op = 'DELETE' then
    perform private.log_action('alert.deleted', old.id::text,
      jsonb_build_object('site_id', old.site_id, 'was_published', old.published_at is not null));
    return null;
  end if;
  action := case
    when new.published_at is not null and (tg_op = 'INSERT' or old.published_at is null)
      then 'alert.published'
    when tg_op = 'INSERT' then 'alert.drafted'
    when new.published_at is null and old.published_at is not null then 'alert.unpublished'
    else 'alert.edited' end;
  perform private.log_action(action, new.id::text,
    jsonb_build_object('site_id', new.site_id, 'confirmed_by_count', new.confirmed_by_count));
  return null;
end;
$$;

create trigger alerts_b_audit
  after insert or update or delete on public.alerts
  for each row execute function private.audit_alerts();

-- Settings -----------------------------------------------------------------------------------------
-- Only an administrator, or the owner by hand, changes them. Never a job.

create function private.guard_app_settings() returns trigger
  language plpgsql security invoker set search_path = ''
as $$
begin
  if tg_op <> 'UPDATE' then
    if private.is_owner_by_hand() then
      return coalesce(new, old);
    end if;
    raise exception 'app_settings has exactly one row' using errcode = '42501';
  end if;
  if not private.is_owner_by_hand() and not private.is_admin() then
    raise exception 'only an administrator can change settings' using errcode = '42501';
  end if;
  new.updated_by := auth.uid();
  new.updated_at := now();
  return new;
end;
$$;

create trigger app_settings_a_guard
  before insert or update or delete on public.app_settings
  for each row execute function private.guard_app_settings();

create function private.audit_app_settings() returns trigger
  language plpgsql security definer set search_path = ''
as $$
begin
  perform private.log_action('settings.changed', 'app_settings',
    jsonb_build_object(
      'old', jsonb_build_object('confirmations_required', old.confirmations_required,
                                'admin_gate_enabled', old.admin_gate_enabled),
      'new', jsonb_build_object('confirmations_required', new.confirmations_required,
                                'admin_gate_enabled', new.admin_gate_enabled)));
  return null;
end;
$$;

create trigger app_settings_b_audit
  after update on public.app_settings
  for each row execute function private.audit_app_settings();

-- Subscribers --------------------------------------------------------------------------------------
-- The address comes from the signed-in account, so nobody can subscribe someone else's email.

create function private.fill_subscriber_email() returns trigger
  language plpgsql security definer set search_path = ''
as $$
declare
  actor uuid := auth.uid();
begin
  if actor is not null then
    select u.email into new.email from auth.users u where u.id = actor;
    new.confirmed_at := null;
  end if;
  return new;
end;
$$;

create trigger subscribers_a_fill_email
  before insert on public.subscribers
  for each row execute function private.fill_subscriber_email();
