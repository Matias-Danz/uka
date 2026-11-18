-- UKA V9 — oprava všech 18 pozadí chatu
-- Spusť jednou v Supabase SQL Editoru.

alter table public.chat_preferences
  drop constraint if exists chat_preferences_theme;

alter table public.chat_preferences
  add constraint chat_preferences_theme
  check (theme in (
    'default','clean','paper','graphite','ice','sky','ocean','mint',
    'aurora','forest','sand','peach','rose','sunset','lavender','violet',
    'midnight','carbon'
  ));
