-- Run in the intended Supabase project (DEV first). Requires authenticated users.
create table if not exists public.uka_moderators (
  user_id uuid primary key references auth.users(id) on delete cascade
);
create table if not exists public.event_submissions (
  id uuid primary key default gen_random_uuid(),
  submitted_by uuid not null default auth.uid() references auth.users(id) on delete cascade,
  title text not null check (length(trim(title)) between 3 and 130),
  artist text not null default '' check (length(artist)<=130),
  category text not null check (category in ('koncert','rave','festival','opera','klub','divadlo','jiné')),
  venue text not null check (length(trim(venue)) between 2 and 120),
  city text not null check (length(trim(city)) between 2 and 100),
  event_date date not null check (event_date >= date '2026-01-01'),
  event_time time,
  price numeric(10,2) check (price between 0 and 1000000),
  ticket_url text check (ticket_url is null or (length(ticket_url)<=2048 and ticket_url ~ '^https://[^[:space:]]+$')),
  description text not null default '' check (length(description)<=1200),
  lat double precision not null check (lat between -90 and 90),
  lng double precision not null check (lng between -180 and 180),
  status text not null default 'pending' check (status in ('pending','approved','rejected')),
  created_at timestamptz not null default now(),
  reviewed_at timestamptz,
  reviewed_by uuid references auth.users(id)
);
create index if not exists event_submissions_status_idx on public.event_submissions(status,created_at);
alter table public.uka_moderators enable row level security;
alter table public.event_submissions enable row level security;
revoke all on public.uka_moderators from anon, authenticated;
revoke all on public.event_submissions from anon, authenticated;
grant select on public.uka_moderators to authenticated;
grant select, insert on public.event_submissions to authenticated;
-- Moderators can read only their own moderator membership.
drop policy if exists moderator_self on public.uka_moderators;
create policy moderator_self on public.uka_moderators for select to authenticated using (user_id = (select auth.uid()));
-- Anyone may read approved events, but not private pending submissions.
drop policy if exists submissions_public_approved on public.event_submissions;
create policy submissions_public_approved on public.event_submissions for select to anon, authenticated using (status = 'approved');
grant select on public.event_submissions to anon;
drop policy if exists submissions_moderator_read on public.event_submissions;
create policy submissions_moderator_read on public.event_submissions for select to authenticated using (exists(select 1 from public.uka_moderators where user_id = (select auth.uid())));
drop policy if exists submissions_submit on public.event_submissions;
create policy submissions_submit on public.event_submissions for insert to authenticated with check (submitted_by = (select auth.uid()) and status = 'pending' and reviewed_at is null and reviewed_by is null);
-- Never grant direct UPDATE/DELETE to browser clients. Moderation through security-definer RPC.
create or replace function public.uka_review_submission(p_id uuid, p_approve boolean)
returns void language plpgsql security definer set search_path = '' as $$
begin
  if auth.uid() is null or not exists(select 1 from public.uka_moderators where user_id=auth.uid()) then
    raise exception 'not_authorized';
  end if;
  update public.event_submissions set status=case when p_approve then 'approved' else 'rejected' end,
    reviewed_at=now(), reviewed_by=auth.uid()
  where id=p_id and status='pending';
  if not found then raise exception 'submission_not_pending'; end if;
end $$;
revoke all on function public.uka_review_submission(uuid,boolean) from public, anon;
grant execute on function public.uka_review_submission(uuid,boolean) to authenticated;
-- IMPORTANT: Add your real auth.users UUID via SQL editor (never via browser):
-- insert into public.uka_moderators(user_id) values ('YOUR-ADMIN-AUTH-USER-UUID');
