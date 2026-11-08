-- UKA admin: oprava RLS pro skrytí/upravy akcí + mazání schválených návrhů.
-- Spusť v Supabase -> SQL Editor jako jeden celek.

create or replace function public.is_uka_moderator()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.uka_moderators m
    where m.user_id = auth.uid()
  );
$$;

revoke all on function public.is_uka_moderator() from public;
grant execute on function public.is_uka_moderator() to authenticated;

-- Klient musí mít SQL oprávnění; RLS níže stále rozhoduje, kdo smí zapisovat.
grant select, insert, update, delete on table public.uka_admin_event_edits to authenticated;
grant delete on table public.event_submissions to authenticated;

-- Opravíme zapisovací RLS pro administrační overrides.
drop policy if exists admin_edits_write on public.uka_admin_event_edits;
create policy admin_edits_write
on public.uka_admin_event_edits
for all
to authenticated
using (public.is_uka_moderator())
with check (public.is_uka_moderator());

-- Moderátor může trvale smazat schválený návrh.
drop policy if exists submissions_moderator_delete on public.event_submissions;
create policy submissions_moderator_delete
on public.event_submissions
for delete
to authenticated
using (public.is_uka_moderator());
