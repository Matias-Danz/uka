# UKA Admin Mode – nasazení nejdřív na Develop

## Obsah
- `admin-mode.html`, `admin-mode.js`: nové administrátorské rozhraní
- `uka-app.js`: veřejný web načítá administrátorské změny ze Supabase
- `scripts/build_public.py`: zahrne Admin Mode do veřejného buildu
- `supabase/admin_mode.sql`: zabezpečené tabulky a RLS

## Bezpečný postup
1. Před úpravami vytvoř commit / zálohu. Přepni na `Develop` a zkontroluj, že nemáš necommitnuté změny.
2. V Supabase **UKA Development** spusť `supabase/event_moderation.sql`, pokud ještě nebyl spuštěn. Poté spusť `supabase/admin_mode.sql`.
3. V `Authentication → Users` najdi UUID svého DEV administrátorského účtu. V DEV SQL editoru spusť:
   `insert into public.uka_moderators(user_id) values ('SEM_UUID_TVEHO_DEV_UCTU') on conflict do nothing;`
   Použij UUID, ne e-mail. Nikomu nedávej service_role key.
4. Přenes do větve `Develop` soubory z tohoto balíčku. **Důležité**: `admin-mode.js` obsahuje produkční Supabase URL a publishable key. Před nasazením na Develop změň tyto dvě hodnoty na DEV Supabase URL a jeho publishable key. Zachovej původní DEV `uka-auth.js`, DEV `_headers` a DEV `moderation.js`. `uka-app.js` načítá Supabase klienta vytvořeného `uka-auth.js`, takže i ten musí být DEV.
5. Commit, Push, úspěšný deploy `uka-dev`; otevři `https://uka-dev.kontakt-uka.workers.dev/admin-mode.html`.
6. Přihlas se DEV administrátorským účtem. Přidej testovací koncert a zkontroluj, že se objeví na DEV webu. Pak ho smaž. Skryj jeden importovaný koncert a ověř, že po reloadu zmizel. Pak jej znovu zobraz.
7. Teprve po ověření opakuj SQL a nasazení na produkci; pro produkci nastav admin UUID z produkčního Supabase.

## Poznámky
- Falešný koncert z původního localStorage se již nemá veřejně zobrazovat; tato verze neodstraňuje samotnou starou hodnotu z prohlížeče.
- U schválených návrhů a importovaných koncertů Admin Mode umožňuje skrýt a změnit základní údaje. Úplné fyzické smazání importovaných dat by bylo neúčinné, protože import by je vrátil. Skrývání je proto správný postup.
- Úpravy importovaných koncertů z databáze mají přednost před importovanými hodnotami. Admin Mode umožňuje přímo editovat vlastní koncerty a mazat je.
- RLS v Supabase je zásadní; samotný HTML formulář není zabezpečení.
- Při otevření na DEV nesmí administrace zobrazovat produkční data. Ověř URL v `admin-mode.js` před push.
- Tento balíček je doplněk k poslední verzi UKA se schvalováním návrhů, nikoli kompletní náhrada celého repozitáře.
