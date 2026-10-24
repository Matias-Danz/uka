# UKA — kompletní společná verze V7 (24. 10. 2026)

Tento ZIP obsahuje **celý kořen repozitáře**, nikoli jen opravu. Rozbal a nakopíruj **OBSAH** složky do kořene `Matias-Danz/uka` (větev `main`). V ZIPu není žádná další nadřazená složka.

## Přesný seznam souborů

```
uka/
├── .github/
│   └── workflows/
│       └── update-events.yml
├── scripts/
│   └── uka_sync.py
├── .gitignore
├── .nojekyll
├── README.md
├── index.html
├── admin.html
├── events.json
├── admin_overrides.json
├── availability_overrides.json
├── price_overrides.json
├── price_links.json
└── requirements.txt
```

**Přesně jeden `index.html`, v kořeni repozitáře.** Nemusí existovat `docs/index.html` ani další zanořené indexy.

**Jediný používaný synchronizátor je `scripts/uka_sync.py`.** Dřívější pomocné `scripts/update_events.py`, `scripts/sync_ticket_info.py` a `scripts/find_public_prices.py` v této verzi nejsou potřeba a workflow je nevolá. Staré `UKA_...` ZIPy a vícenásobné kopie HTML také v repozitáři nenechávej.

## Nejbezpečnější instalace přes GitHub Desktop

1. Na GitHubu si pro jistotu stáhni zálohu současného repozitáře (Code > Download ZIP), zejména pokud jsi nedávno měnil akce v administraci.
2. V GitHub Desktop otevři lokální klon projektu `uka` na větvi `main` (případně repozitář nejprve naklonuj).
3. V klonu vymaž **staré pracovní soubory projektu**, ale ponech skrytou složku `.git` (ta obsahuje historii!). Pozor na vlastní přidané obrázky ve `media/`: pokud existují, uchovej je, protože nejsou součástí této zálohy.
4. Do klonu nakopíruj **obsah** rozbaleného tohoto ZIPu (ne celý ZIP a ne další podsložku). Ve Finderu na Macu skryté soubory zobrazíš `Cmd + Shift + .`.
5. V GitHub Desktop zkontroluj změny, zadej `UKA V7 – jednotná kompletní verze`, klikni na **Commit to main** a následně **Push origin**.
6. GitHub > Settings > Pages > Build and deployment: Source musí být **GitHub Actions**. V GitHub > Settings > Secrets and variables > Actions musí být uložen `TICKETMASTER_API_KEY`, pokud chceš Discovery API (nemusí být vyplněn pro samotné spuštění).
7. V GitHub > Actions > UKA — aktualizovat akce a zveřejnit web > Run workflow sleduj jednotlivé kroky. Když běh selže, otevři **první červený krok**; souhrnná hláška `exit code 1` sama neříká proč.

## Při nahrání pouze přes web GitHubu

`Add file > Upload files` doplní nebo nahradí soubory, ale **neodstraní** staré nepotřebné soubory. Ty je nutné odstranit samostatně. Na Macu je `.github` skrytá, zapni `Cmd + Shift + .`.

## Jaká data ZIP obsahuje

- `index.html`: poslední z dostupných plných verzí (Ticketmaster V4, chytré hledání V3).
- `scripts/uka_sync.py` a `.github/workflows/update-events.yml`: poslední oprava synchronizace V6, už bez `--dry-run` v hodinové aktualizaci.
- `events.json`: lokálně dostupný stav **343 akcí** z 24. 10. 2026, ne ověřený živý stav dnešního GitHubu. **Pokud máš na GitHubu novější data nebo ruční úpravy, nejprve je zazálohuj a podle potřeby je vrať**. Totéž platí pro `admin_overrides.json`, `price_overrides.json`, `availability_overrides.json`, `price_links.json` a obrázky v `media/`.
- Žádné API klíče nejsou v ZIPu. Klíče zadávej do GitHub Secrets, nikoli do souborů.

## Co bylo vyzkoušeno

Kontrola syntaxe Pythonu, syntaktická kontrola inline JavaScriptu, JSON, struktura ZIPu, běh `scripts/uka_sync.py --check` a běh offline testu bez přístupu k internetu. Nemáme zaručený úspěch vzdáleného běhu GitHub Actions ani přístup k neveřejnému Ticketmaster inventáři.
