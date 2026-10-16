# UKA v5 — jak ji zdarma zapnout na GitHubu

## Nejprve jen vyzkoušej aplikaci

Stáhni samostatný soubor `UKA_v5_otevri.html` a na počítači jej otevři dvojklikem. Zobrazí se 74 připravených akcí; 58 má URL na plakát.
Tohle je lokální kopie: při zavření ani po opětovném otevření nedostane automaticky nové akce.

## Jak vytvořit živý web (bez programování a bez Base44)

**Potřebuješ jen bezplatný účet na GitHub.com a počítač.**

1. Otevři `https://github.com` a založ účet nebo se přihlas.
2. Otevři `https://github.com/new`.
3. Do `Repository name` napiš `uka` a nastav `Public` (Github Pages zdarma pro veřejné repo).
4. Klikni `Create repository`.
5. Na počítači rozbal ZIP. V rozbalené složce jsou `index.html`, `events.json`, `requirements.txt`, `README.md`, `scripts/`, `.github/` a `.nojekyll`.
6. Na GitHubu v repozitáři klikni `Add file` -> `Upload files`. Do plochy přetáhni **obsah rozbalené složky** (včetně složek `scripts` a `.github`; ne ZIP samotný). GitHub podporuje přetažení složky. **Na Macu je `.github` skrytá složka:** v otevřeném Finderu zmáčkni `Command + Shift + .` (tečka), aby byla vidět, pak vyber všechny položky a přetáhni je.
7. Dole klikni `Commit changes` (někdy `Propose changes`) a potvrď vložení do větve `main`.
8. Zkontroluj, že v seznamu vidíš `index.html`, `events.json` a adresáře `scripts` a `.github`. Když `.github` chybí, nepoběží automatizace.
9. Otevři `Settings` -> v levém menu `Pages` -> sekci `Build and deployment`, u `Source` vyber **`GitHub Actions`**. **NEVYBÍREJ `Deploy from a branch`**, protože tato verze vydává stránku stejným workflow, které aktualizuje akce.
10. Klikni `Actions` -> `UKA — aktualizovat akce a zveřejnit web` -> `Run workflow` -> znovu `Run workflow`. Počkej na zelenou fajfku (může to trvat několik minut).
11. Otevři `Settings` -> `Pages` -> `Visit site`. Adresa bude `https://TVEJMENO.github.io/uka/`.

## Co se bude dít

- GitHub Actions může přibližně každou hodinu spustit skript a aktualizovat `events.json`, potom **rovnou publikuje nový web**. GitHub může plánované spuštění opozdit.
- Automatický zdroj je zatím jen **oficiální program O2 areny**, pokud je přístup povolen. Když import nemá co přidat nebo mu zdroj blokuje přístup, nic nového nepřibude. Ověř v záložce Actions / logs, co importer napsal.
- Stávající ručně doložené akce z GoOutu a Eventlooku se uchovají, **neimportují se odtamtud automaticky nové**. K tomu potřebujeme dohodnout autorizovaný feed/API.
- Proběhlé akce se z aplikace skryjí automaticky podle data v ČR; pravidelná úloha je následně smaže i ze souboru dat.
- Pokud celý web jen stáhneš jako HTML soubor na disk, automatizace na tvém počítači nepoběží. Aktualizuje se pouze stránka na GitHub Pages.
- GitHub může v neaktivním veřejném repozitáři po 60 dnech zastavit plánované workflow; lze ho obnovit v `Actions`.
- Fotky jsou zobrazené jako odkazy na obrazové servery pořadatelů, neuložené kopie. Pro komerční zveřejnění vyřeš práva a souhlasy. Pokud server obrázek zablokuje, UKA zobrazí náhradní grafiku.

## Pokud GitHub automatizaci nenabízí

Zkontroluj, zda existuje `.github/workflows/update-events.yml` (v seznamu souborů klikni `.github` > `workflows`). Pokud ne, vytvoř ho přes `Add file` -> `Create new file`, do názvu zapiš `.github/workflows/update-events.yml` a vlož obsah z ZIPu. Zkontroluj také složku `scripts/`, tam musí být `update_events.py`. Pokud automatizace hlásí chybu `403` při ukládání `events.json`, zkontroluj v `Settings` -> `Actions` -> `General` -> `Workflow permissions`, zda oprávnění repozitáře umožňují zápis (organizace to může omezit).

## Technické detaily pro později

- Frontend: jediný HTML soubor bez Base44.
- Data: `events.json`, v HTML je offline záložní seznam se stejnými událostmi.
- Automatizace: `.github/workflows/update-events.yml` (každou hodinu, také při přidání souborů a ručně).
- Importér: `scripts/update_events.py` (zdroje respektují robots.txt; datum a místo musí být ověřené).
