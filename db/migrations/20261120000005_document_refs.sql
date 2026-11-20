-- What a reviewer may know about any document, restricted or not. See BUILD_PLAN.md section 7.
--
-- A reviewer confirms a site only after opening the source record. For a list that names
-- people the reviewer cannot read our stored copy. They still need the public address of the
-- record, when we fetched it and its hash. This view gives exactly that and nothing else: no
-- text and no metadata.
--
-- Like public_alerts, the view runs with its owner's rights on purpose, and its own WHERE
-- clause is the gate.

create view public.document_refs
  with (security_invoker = false, security_barrier = true)
as
select
  d.id,
  d.source_id,
  s.name as source_name,
  s.slug as source_slug,
  d.url,
  d.retrieved_at,
  d.sha256,
  d.restricted
from public.documents d
join public.sources s on s.id = d.source_id
where (select private.is_approved_reviewer());

revoke all on public.document_refs from anon, authenticated, public;
grant select on public.document_refs to authenticated, service_role;
