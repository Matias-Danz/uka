-- Run AFTER event_moderation.sql in DEVELOPMENT Supabase first.
-- Administrator privileges come exclusively from uka_moderators, never from browser state.
create table if not exists public.uka_admin_event_edits (
  event_id text primary key check (length(event_id) between 1 and 200),
  hidden boolean not null default false,
  fields jsonb not null default '{}'::jsonb check (jsonb_typeof(fields) = 'object' and octet_length(fields::text) < 10000),
  updated_at timestamptz not null default now()
);
create table if not exists public.uka_admin_events (
  id uuid primary key default gen_random_uuid(),
  title text not null check (length(trim(title)) between 3 and 130),
  artist text not null default '',
  category text not null check (category in ('koncert','rave','festival','opera','klub','divadlo','jiné')),
  venue text not null check (length(trim(venue)) between 2 and 120),
  city text not null check (length(trim(city)) between 2 and 100),
  event_date date not null,
  event_time time,
  price numeric(10,2) check (price between 0 and 1000000),
  ticket_url text check (ticket_url is null or (length(ticket_url)<=2048 and ticket_url ~ '^https://[^[:space:]]+$')),
  description text not null default '' check (length(description)<=1200),
  lat double precision not null check (lat between -90 and 90),
  lng double precision not null check (lng between -180 and 180),
  created_at timestamptz not null default now()
);
alter table public.uka_admin_event_edits enable row level security;
alter table public.uka_admin_events enable row level security;
revoke all on public.uka_admin_event_edits from anon, authenticated;
revoke all on public.uka_admin_events from anon, authenticated;
grant select on public.uka_admin_event_edits, public.uka_admin_events to anon, authenticated;
grant insert, update, delete on public.uka_admin_event_edits, public.uka_admin_events to authenticated;
-- Public can read the resulting event state; only moderators may mutate it.
drop policy if exists admin_edits_read on public.uka_admin_event_edits;
create policy admin_edits_read on public.uka_admin_event_edits for select to anon, authenticated using (true);
drop policy if exists admin_events_read on public.uka_admin_events;
create policy admin_events_read on public.uka_admin_events for select to anon, authenticated using (true);
drop policy if exists admin_edits_write on public.uka_admin_event_edits;
create policy admin_edits_write on public.uka_admin_event_edits for all to authenticated
  using (exists(select 1 from public.uka_moderators where user_id=(select auth.uid())))
  with check (exists(select 1 from public.uka_moderators where user_id=(select auth.uid())));
drop policy if exists admin_events_write on public.uka_admin_events;
create policy admin_events_write on public.uka_admin_events for all to authenticated
  using (exists(select 1 from public.uka_moderators where user_id=(select auth.uid())))
  with check (exists(select 1 from public.uka_moderators where user_id=(select auth.uid())));
-- Approved proposals remain in event_submissions. Moderators can hide them using event_id 'submission-<uuid>'.
-- Imported events remain in events.json; moderators can hide them using their source event ID.
