#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UKA: conservative public Ticketmaster CZ prices rendered in real Chromium.

Only reads visibly rendered, public 'CZK per ticket' category prices on the
individual event page. No login, checkout, anti-bot bypass, CAPTCHA handling,
proxy rotation, or authenticated/hidden endpoints. Stops at 401/403/429 or
access challenges. If the page does not expose a price, nothing is invented.

Run after uka_sync.py. Does not alter any non-Ticketmaster source or manual
price. Persists attempts to avoid re-requesting the same pages every hour.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import unicodedata
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
EVENTS_FILE = ROOT / 'events.json'
STATE_FILE = ROOT / 'tm_browser_state.json'
ALLOWED_HOSTS = {'www.ticketmaster.cz', 'ticketmaster.cz'}
MIN_RECHECK_DAYS = 3
BLOCKED_COOLDOWN_HOURS = 24
MAX_CHECKS = 4

# Only prices *per ticket*, rather than fees, packages mentioned in text,
# prices in related-event suggestions, or arbitrary numbers in embedded JS.
AMOUNT = r'(?:\d{1,3}(?:[ \u00a0\u202f.]\d{3})+|\d{1,6})(?:[,\.]\d{2})?'
PER_TICKET_RE = re.compile(
    rf'(?<!\d)({AMOUNT})\s*(?:Kč|CZK)\s*'
    r'(?:za\s+kus|za\s+vstupenku|per\s+ticket|each|/\s*ks)',
    flags=re.I,
)
START_MARKERS = ('Všechny ceny', 'All prices', 'Všechny sekce', 'All sections',
                 'Vyberte vstupenky', 'Select Tickets')
STOP_MARKERS = ('Vstupenek v košíku:', 'Tickets in your cart:',
                'Limit vstupenek na akci:', 'Najít vstupenky', 'Find Tickets')
CHALLENGE_MARKERS = ('access denied', 'are you a human', 'prove you are human',
                     'unusual traffic', 'přístup odepřen', 'captcha',
                     'verify you are human', 'just a moment')


def normalize_title(text: str) -> str:
    text = unicodedata.normalize('NFKD', str(text or '').casefold())
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return ' '.join(re.findall(r'[a-z0-9]+', text))


def sane_url(value: str) -> bool:
    try:
        p = urlparse(value)
        return (p.scheme == 'https' and p.hostname in ALLOWED_HOSTS
                and p.username is None and p.password is None
                and (p.port is None or p.port == 443)
                and p.path.startswith('/event/') and len(value) < 1000)
    except ValueError:
        return False


def belongs_to_event(page_heading: str, event_title: str) -> bool:
    """Simple confirmation that a redirected purchase page is for this show."""
    a, b = normalize_title(page_heading), normalize_title(event_title)
    if not a or not b:
        return False
    if a == b or (len(a) >= 9 and a in b) or (len(b) >= 9 and b in a):
        return True
    a_first = a.split()[0] if a.split() else ''
    b_first = b.split()[0] if b.split() else ''
    return (a_first == b_first and len(a_first) >= 4 and
            SequenceMatcher(None, a, b).ratio() >= .60)


def to_czk(s: str) -> int | None:
    s = s.strip().replace('\xa0', ' ').replace('\u202f', ' ').replace(' ', '')
    # Normalize Czech 1.190,00 / 1 190,00 and English 1190.00; avoid
    # treating decimal cents as thousands (890.00 must mean 890).
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    elif '.' in s:
        if re.search(r'\.\d{2}$', s):
            s = s.replace('.', '', s.count('.') - 1)
        else:
            s = s.replace('.', '')
    try:
        number = float(s)
    except ValueError:
        return None
    if not (0 < number <= 200000):
        return None
    return round(number)


def visible_ticket_prices(body_text: str) -> tuple[int | None, int | None]:
    """Parse only a visible ticket-category area on a public event page."""
    text = re.sub(r'\s+', ' ', body_text or '').strip()
    # Hard guard: we do not scrape general page descriptions or price widgets
    # from other events. Without the purchase price controls we leave blank.
    markers = [text.find(x) for x in START_MARKERS if text.find(x) >= 0]
    if not markers:
        return None, None
    start = min(markers)
    stops = [text.find(x, start + 1) for x in STOP_MARKERS if text.find(x, start + 1) >= 0]
    end = min(stops) if stops else min(len(text), start + 12000)
    section = text[start:end]
    amounts = sorted({n for m in PER_TICKET_RE.finditer(section)
                      if (n := to_czk(m.group(1))) is not None})
    if not amounts:
        return None, None
    return amounts[0], amounts[-1]


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.uka-prices-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write('\n')
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def load_state() -> dict:
    try:
        data = json.loads(STATE_FILE.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def blocked_recently(state: dict, now: datetime) -> bool:
    try:
        last = datetime.fromisoformat(state['blocked_until'])
        return last.tzinfo is not None and now < last
    except (ValueError, TypeError, KeyError):
        return False


def due(event: dict, today: date) -> bool:
    if not str(event.get('id', '')).startswith('ticketmaster-'):
        return False
    if not sane_url(str(event.get('ticket_url') or '')):
        return False
    try:
        if date.fromisoformat(str(event.get('date', ''))) < today:
            return False
    except ValueError:
        return False
    # Only fill missing prices, or refresh prices this browser previously found.
    if event.get('price') is not None and event.get('price_source') != 'Ticketmaster (stránka)':
        return False
    checked = event.get('tm_browser_checked_at')
    if checked:
        try:
            if (today - date.fromisoformat(str(checked)[:10])).days < MIN_RECHECK_DAYS:
                return False
        except ValueError:
            pass
    return True


def select_events(items: list[dict], now: datetime, limit: int) -> list[dict]:
    candidates = [item for item in items if isinstance(item, dict) and due(item, now.date())]
    # Earliest concerts with missing prices first; don't starve new entries.
    candidates.sort(key=lambda e: (e.get('price') is not None,
                                    str(e.get('tm_browser_checked_at') or ''),
                                    e.get('date', '9999')))
    return candidates[:limit]


class BrowserPriceReader:
    def __init__(self, browser):
        self.browser = browser
        self.blocked = False

    def read(self, url: str, title: str) -> tuple[tuple[int | None, int | None], str]:
        context = self.browser.new_context(locale='cs-CZ', timezone_id='Europe/Prague',
                                           viewport={'width': 1280, 'height': 880})
        page = context.new_page()
        try:
            response = page.goto(url, wait_until='domcontentloaded', timeout=24000)
            status = response.status if response else 0
            if status in (401, 403, 429):
                self.blocked = True
                return (None, None), f'HTTP {status} – přístup omezen'
            if not response or status >= 400:
                return (None, None), f'HTTP {status}'
            # Navigation must not end on an unexpected site.
            if not sane_url(page.url):
                return (None, None), 'přesměrování mimo stránku akce'
            try:
                page.wait_for_function(
                    "() => /(?:Kč\\s*za\\s*kus|CZK\\s*per\\s*ticket)/i.test(document.body.innerText)",
                    timeout=6500,
                )
            except Exception:
                pass
            body = page.locator('body').inner_text(timeout=5000)
            lowered = body.casefold()
            if any(marker in lowered for marker in CHALLENGE_MARKERS):
                self.blocked = True
                return (None, None), 'ochrana proti automatickému přístupu'
            heading = page.locator('h1').first.inner_text(timeout=3500)
            if not belongs_to_event(heading, title):
                return (None, None), 'nesouhlasí název koncertu'
            price = visible_ticket_prices(body)
            return price, 'cena nalezena' if price[0] is not None else 'bez veřejně uvedené ceny'
        except Exception as exc:
            # Keep diagnostics informative without logging page URLs or cookies.
            err = str(exc)
            net = re.search(r'net::(ERR_[A-Z_]+)', err)
            if net:
                return (None, None), f'síťový problém ({net.group(1)})'
            return (None, None), f'načtení selhalo ({type(exc).__name__})'
        finally:
            context.close()


def run(limit: int, dry_run: bool, force: bool, event_id: str | None = None) -> int:
    now = datetime.now(timezone.utc)
    try:
        payload = json.loads(EVENTS_FILE.read_text(encoding='utf-8'))
        events = payload['events']
        if not isinstance(events, list):
            raise ValueError('events není seznam')
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f'TM PROHLÍŽEČ: databáze se nedá číst ({type(exc).__name__})')
        return 1
    state = load_state()
    if not force and blocked_recently(state, now):
        print('TM PROHLÍŽEČ: web minule odmítl přístup; pauza 24 h, bez dalších požadavků')
        return 0
    selected = select_events(events, now, limit)
    if event_id:
        match = next((e for e in events if e.get('id') == event_id and
                      sane_url(str(e.get('ticket_url') or '')) and
                      e.get('price') is None), None)
        selected = [match] if match else []
    if not selected:
        print('TM PROHLÍŽEČ: žádné ceny ke kontrole')
        return 0
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('TM PROHLÍŽEČ: chybí balíček playwright v requirements.txt')
        return 1
    attempted = found = blocked = 0
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True, executable_path=os.environ.get('UKA_CHROMIUM_PATH') or None)
            reader = BrowserPriceReader(browser)
            try:
                for event in selected:
                    # Plain browser – no stealth mode, logins, cookies or proxy tricks.
                    (low, high), diagnostic = reader.read(str(event['ticket_url']), str(event.get('title') or ''))
                    attempted += 1
                    print(f'TM PROHLÍŽEČ: {event.get("title", "akce")[:70]}: {diagnostic}'
                          + (f' (od {low} Kč)' if low is not None else ''))
                    if reader.blocked:
                        blocked = 1
                        if not dry_run:
                            state['blocked_until'] = (now + timedelta(hours=BLOCKED_COOLDOWN_HOURS)).isoformat()
                        print('TM PROHLÍŽEČ: ochrana webu, další požadavky zastaveny')
                        break
                    if not dry_run:
                        event['tm_browser_checked_at'] = now.date().isoformat()
                    if low is not None:
                        found += 1
                        if not dry_run:
                            event['price'] = low
                            event['price_max'] = high if high != low else None
                            event['price_from'] = True
                            event['price_source'] = 'Ticketmaster (stránka)'
                            event['price_checked_at'] = now.date().isoformat()
                    time.sleep(1.0)
            finally:
                browser.close()
    except Exception as exc:
        print(f'TM PROHLÍŽEČ: Chromium se nepodařilo spustit ({type(exc).__name__});'
              ' akce a ceny ponechány beze změny')
        return 0  # A browser check must not prevent the regular update/publish.
    if not dry_run:
        if found:
            atomic_json(EVENTS_FILE, payload)
        elif any('tm_browser_checked_at' in event for event in selected):
            atomic_json(EVENTS_FILE, payload)
        if blocked:
            atomic_json(STATE_FILE, state)
        elif STATE_FILE.exists() and 'blocked_until' in state:
            state.pop('blocked_until', None)
            atomic_json(STATE_FILE, state)
    print(f'TM PROHLÍŽEČ – VÝSLEDEK: zkontrolováno {attempted}, '
          f'nově nalezených cen {found}, přístup blokován {bool(blocked)}, '
          f'režim {"TEST bez zápisu" if dry_run else "uložení"}')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='UKA – veřejné ceny Ticketmasteru v Chromiu')
    parser.add_argument('--limit', type=int, default=MAX_CHECKS, help='Max. 1–8 stránek za běh')
    parser.add_argument('--dry-run', action='store_true', help='Bez jakýchkoli zápisů')
    parser.add_argument('--force', action='store_true', help='Jednorázově ignorovat místní pauzu po blokaci')
    parser.add_argument('--event-id', help='Ověřit jen jednu akci podle ID v events.json')
    args = parser.parse_args()
    if not 1 <= args.limit <= 8:
        parser.error('--limit musí být od 1 do 8')
    return run(args.limit, args.dry_run, args.force, args.event_id)


if __name__ == '__main__':
    sys.exit(main())
