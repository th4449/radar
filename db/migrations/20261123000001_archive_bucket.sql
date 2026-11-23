-- The archive's bucket in the hosted project's storage. See collectors/hosted_archive.py and
-- BUILD_PLAN.md section 3.
--
-- Every stored file goes in this one bucket, under its hash. The bucket is private and this
-- migration gives nobody a policy on it, so only the service key reads or writes a file. A
-- reviewer opens a record at the agency's own address, never from here.
--
-- A database started without the storage service has no storage tables. The bucket is then
-- not made, and nothing else in the radar's schema depends on it.

do $$
begin
  if to_regclass('storage.buckets') is null then
    raise notice 'no storage tables here: the archive bucket is not made';
    return;
  end if;
  insert into storage.buckets (id, name, public)
  values ('archive', 'archive', false)
  on conflict (id) do nothing;
end
$$;
