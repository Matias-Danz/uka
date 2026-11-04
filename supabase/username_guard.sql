-- Run in the Supabase SQL Editor for EACH project, then enable
-- Authentication > Hooks > Before User Created > Postgres function.
-- IMPORTANT: This hook must be enabled to enforce username policy server-side.
create or replace function public.uka_check_username_before_signup(event jsonb)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  uname text := coalesce(event->'user'->'user_metadata'->>'username', '');
  normalized text;
begin
  normalized := lower(uname);
  normalized := translate(normalized, '01345789', 'oieastbg');
  normalized := replace(normalized, '_', '');
  if uname !~ '^[A-Za-z0-9_]{3,24}$'
     or normalized ~ '(nigg|fagg|kike|spic|chink|retard|nazi|hitler)' then
    return jsonb_build_object('error', jsonb_build_object('http_code', 400, 'message', 'username_not_allowed'));
  end if;
  return event;
end;
$$;
revoke all on function public.uka_check_username_before_signup(jsonb) from public, anon, authenticated;
grant execute on function public.uka_check_username_before_signup(jsonb) to supabase_auth_admin;
