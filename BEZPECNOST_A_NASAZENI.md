# UKA – bezpečnostní aktualizace V3 (30. 10. 2026)

## Před nasazením
1. Zálohuj GitHub repozitář a soubory. Nahraj celý obsah této složky do kořene repozitáře (bez `dist/`), ne jen `index.html`.
2. Cloudflare: build `python3 scripts/build_public.py`, deploy `npx wrangler deploy` podle stávající konfigurace. Ověř, že výsledný hosting skutečně publikuje `dist/` a že hlavičky `_headers` jsou respektovány. **Cloudflare Workers** nerespektují `_headers` automaticky; v takovém případě nastav CSP a hlavičky ve Workeru.
3. GitHub Pages ignoruje `_headers`; ochranná CSP je také v meta tagu `index.html`, ale hlavičky jako HSTS, X-Frame-Options a frame-ancestors musí nastavit hosting.
4. Supabase → Database: ověř RLS na každé veřejně dostupné tabulce; v současném frontendu se žádná profilová tabulka nevytváří. V žádném případě nedávej `service_role`/secret klíč do JS ani GitHubu.
5. Supabase → Authentication: potvrzení e-mailu, minimální délka hesla na serveru, rate limits, CAPTCHA, přesné povolené Redirect URLs, zabezpečené SMTP.
6. Vypni veřejné registrace, dokud nezkontroluješ nastavení databáze, hlavičky nasazeného webu a reálné přihlášení / obnovu hesla v prohlížeči.
7. `admin.html` je pouze v repozitáři, **nesmí být v `dist/`**. PAT do browseru zůstává rizikový. Používej pouze úzce omezený krátkodobý token na vlastním důvěryhodném zařízení, nebo přejdi na serverovou správu. Tato aktualizace admin backend nevytváří.

## Co bylo změněno
- Inline JS a CSS hlavní stránky přesunuty do `uka-app.js`, `uka-theme.js`, `uka.css` pro přísnější CSP.
- Odstraněn inline `onerror` a ošetřeny odkazy na vstupenky/obrázky (pouze HTTPS, bez credentials).
- Veřejná data filtrují pole a URL i u administračních úprav a ručních akcí; načítají skutečné override soubory.
- Přidány `_headers` pro Cloudflare Pages, meta CSP pro GitHub Pages, přísnější heslo na klientovi a opětovné ověření současným heslem při běžné změně hesla.
- Workflow spouští testy a reaguje na změny nových assetů.

## Co není vyřešeno a nelze ověřit offline
- Skutečné Supabase RLS, SMTP, CAPTCHA, serverová politika hesel, redirect URLs a nastavení GitHubu/Cloudflare.
- Přístupový token admina v prohlížeči; doporučený server-side backend nebyl implementován.
- CDN knihovny MapLibre a Supabase nejsou self-hosted ani opatřené SRI (potřebuje kontrolované stažení, pinování a ověření hashů). CSP je omezuje na jsDelivr.
- Účet zatím nemá serverově zajištěné unikátní username, synchronizované favorites, export/smazání účtu a finální GDPR dokumentaci.
- Není proveden nezávislý penetrační test ani ověření na produkční doméně. Neexistuje absolutní bezpečnost.

## Tři kontrolní vrstvy
1. Statika: `node --check uka-app.js`, `node --check uka-auth.js`, `python -m py_compile scripts/build_public.py`.
2. Testy: `python -m unittest discover -s tests -v` + vlastní bezpečnostní testy.
3. Publikace: `python scripts/build_public.py`, kontrola dist a ruční test v prohlížeči / kontrola response headers.
