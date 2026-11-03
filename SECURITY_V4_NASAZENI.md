# UKA Security V4 – změny a nasazení

## Změny
- `admin.html` již neobsahuje GitHub PAT editor ani volání GitHub API. Úpravy souborů se provádějí přes přihlášené rozhraní GitHubu (GitHub kontroluje oprávnění). Původní pohodlné administrační GUI tímto **přestane fungovat**. Pro pohodlné zabezpečené GUI je nutné vytvořit serverový backend s autentizací a autorizací.
- `scripts/validate_data.py` kontroluje JSON syntaxi, duplicitní klíče, strukturu, identifikátory, datum, ceny, souřadnice, bezpečné odkazy a délky vybraných polí. Validace běží před buildem a před/po automatickém importu v GitHub Actions.
- GitHub Actions ukládají snapshot pěti JSON souborů jako artefakt s uchováním 30 dnů. Historie Git commitů je další vrstva obnovy. Retence záloh závisí na nastavení a dostupnosti GitHub Actions, nejsou to off-site zálohy.
- Přidány regresní testy.

## Důležité limity
- `_headers` se použijí pouze na hostingu, který je respektuje (typicky Cloudflare Pages). U Cloudflare Workers je nutné hlavičky nastavit ve Workeru. Ověř na produkci v DevTools / curl -I.
- Repo musí být zabezpečené (2FA/passkeys, branch protection, minimální oprávnění spolupracovníků, žádné tokeny v commitech). Pokud starý token někdy unikl, okamžitě jej zruš.
- Ověřit Supabase RLS na všech tabulkách, ochranu registrací, reset hesla a povolené redirect URLs. Tyto kroky nelze ověřit z lokálního kódu.
- JSON obsah je veřejný; nesmí obsahovat osobní údaje, tajné klíče ani interní poznámky.
- Validátor může odmítnout nově importované záznamy, které nesplňují schéma. V takovém případě GitHub Actions zastaví publikaci, je třeba opravit data/import, nikoli vypnout validaci.

## Instalace
1. Zazálohuj současný repozitář. Nahraj všechny soubory ZIP do kořene repozitáře, ne adresář `dist`.
2. Spusť `python scripts/validate_data.py`, `python -m unittest discover -s tests -v`, `python scripts/build_public.py`.
3. Zkontroluj GitHub Actions a deployment Cloudflare; otestuj web v prohlížeči a odezvy hlaviček.
4. Ruční úpravy: GitHub → soubor `admin_overrides.json` nebo `availability_overrides.json` → Edit → Commit. Pro ochranu změn doporučujeme pull requesty a schvalování.
5. Před veřejným spuštěním ověř RLS a bezpečnostní nastavení Supabase.
