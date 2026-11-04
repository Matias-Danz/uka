# UKA: návrhy koncertů se schvalováním

**Nejdřív DEV, až potom main.** Připravené soubory používají produkční Supabase URL. Při přenosu do `Develop` zachovej jeho vlastní URL a publishable key **v `uka-auth.js` i `moderation.js`**. Nezapisuj service_role key do webu.

1. V Supabase DEVELOPMENT otevři SQL Editor a spusť `supabase/event_moderation.sql`.
2. V Supabase DEVELOPMENT > Authentication > Users vytvoř/použij svůj potvrzený administrátorský účet a zkopíruj jeho **UUID**.
3. V SQL Editoru spusť: `insert into public.uka_moderators(user_id) values ('TVE-UUID');` (nahraď UUID; účet musí existovat).
4. Přenes soubory `uka-app.js`, `uka-auth.js`, `moderation.html`, `moderation.js` a `scripts/build_public.py` do `Develop`. Pozor: přenos `uka-auth.js` musí zachovat DEV URL/klíč. Přenes i SQL a tento návod.
5. Build/deploy dev a otevři `https://uka-dev.kontakt-uka.workers.dev/moderation.html`. Přihlas se administrátorským účtem.
6. Zkus nepřihlášený návrh (musí požadovat přihlášení), přihlášený návrh (nesmí se zobrazit veřejně), zamítnutí (nesmí se zobrazit) a schválení (po obnovení se zobrazí). Ověř v Supabase statusy `pending`, `rejected`, `approved`.
7. Po úspěchu zopakuj SQL na PRODUKČNÍM Supabase, zapiš tam UUID svého produkčního administrátora, přenes otestované soubory do `main` s produkčními URL/klíči.

**Důležité:** Před spuštěním SQL nefunguje odesílání návrhů. Bez vložení admin UUID nelze návrhy schvalovat. Schválené návrhy se zobrazují v aplikaci z Supabase, nikoli z GitHub `events.json`; jejich zveřejnění nevyžaduje GitHub commit. Původní lokální akce jsou z veřejného seznamu ignorovány (nesmaže se jejich uložený obsah z prohlížeče). `admin.html` zůstává původní správou importovaných dat, nová moderace je na `/moderation.html`.

**Bezpečnostní omezení:** RLS brání klientovi zveřejňovat vlastní návrhy nebo schvalovat bez oprávnění. Před veřejným spuštěním doplň ochranu proti spamu a automatizovanému odesílání (např. rate limiting na serveru/CAPTCHA). SQL není aktivováno automaticky a živé end-to-end testy nebyly provedeny.
