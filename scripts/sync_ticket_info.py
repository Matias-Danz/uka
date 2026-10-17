#!/usr/bin/env python3
"""UKA: conservative ticket sales/availability/price enrichment.

Runs AFTER scripts/update_events.py. Does not require modifications to the
existing concert importer and never treats missing info as sold out.
Only Ticketmaster's authorized Inventory Status API can verify primary inventory.
Discovery supplies sales *phase* (not seat availability).
Official O2 pages supply explicitly advertised public-sale notices.
"""
from __future__ import annotations

import json
from difflib import SequenceMatcher
import math
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
EVENT_FILE = ROOT / 'events.json'
NOW = lambda: datetime.now(timezone.utc)
UA = 'UKA-MusicEvents/0.5 (event metadata; robots compliant)'
TM_DETAIL = 'https://app.ticketmaster.com/discovery/v2/events/{id}.json'
TM_INVENTORY = 'https://app.ticketmaster.com/inventory-status/v1/availability'
O2_DOMAINS = {'www.o2arena.cz', 'www.o2universum.cz'}
DETAIL_LIMIT = 18
O2_LIMIT = 12
INVENTORY_LIMIT = 20
AUTO_SOURCES = {'Ticketmaster Inventory Status API', 'O2 official'}
STATUS_TTLS_HOURS = {'available': 36, 'low': 18, 'temporarily_sold_out': 18, 'sold_out': 72}
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': UA, 'Accept-Language': 'cs-CZ,cs;q=0.9'})


def timestamp(now=None):
    return (now or NOW()).isoformat(timespec='seconds').replace('+00:00', 'Z')


def parse_dt(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def stale(value, hours, now=None):
    old = parse_dt(value)
    return old is None or ((now or NOW()) - old) >= timedelta(hours=hours)


def _nice_status(value):
    return str(value or '').strip().upper()


def inventory_state(row):
    """Map primary inventory only; resale never counts as primary availability.

    No available tickets != a definitive event-level sold-out announcement.
    During an active sales window, it is *temporarily* unavailable.
    """
    if not isinstance(row, dict):
        return None
    return {
        'TICKETS_AVAILABLE': 'available',
        'FEW_TICKETS_LEFT': 'low',
        'TICKETS_NOT_AVAILABLE': 'temporarily_sold_out',
    }.get(_nice_status(row.get('status')))


def inventory_price(row):
    if not isinstance(row, dict) or str(row.get('currency', '')).upper() != 'CZK':
        return None
    if _nice_status(row.get('status')) not in {'TICKETS_AVAILABLE', 'FEW_TICKETS_LEFT'}:
        return None
    amounts=[]
    for price in (row.get('priceRanges') or []):
        if not isinstance(price, dict) or str(price.get('type', '')).lower() != 'primary':
            continue
        try:
            mn, mx = float(price['minPrice']), float(price.get('maxPrice', price['minPrice']))
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if not (math.isfinite(mn) and math.isfinite(mx) and 0 < mn <= mx <= 200_000):
            continue
        amounts.append((mn, mx, bool(price.get('listingsExtendBeyondMax'))))
    if not amounts:
        return None
    low = round(min(x[0] for x in amounts))
    # Inventory API may cap max at 2,000 CZK; don't show a false maximum.
    high = None if any(x[2] for x in amounts) else round(max(x[1] for x in amounts))
    return low, high


def safe_price_update(event, low, high, source, checked):
    """Respect manual and venue prices; fill missing values or refresh inventory prices."""
    if low is None:
        return False
    old_source = event.get('price_source')
    if event.get('price') is not None and old_source not in {'Ticketmaster Inventory Status API', 'Ticketmaster', 'Ticketmaster (stránka)'}:
        return False
    if (event.get('price'), event.get('price_max'), event.get('price_source')) == (low, high, source):
        event['price_checked_at'] = checked[:10]
        return False
    event.update({'price': low, 'price_max': high, 'price_source': source,
                  'price_checked_at': checked[:10], 'price_from': True})
    event.pop('price_note', None)
    return True


def update_availability(event, state, source, checked, note=''):
    """Only update automated data; never override a separately curated manual status."""
    if state not in STATUS_TTLS_HOURS:
        return False
    old_source = str(event.get('ticket_status_source') or '')
    if event.get('ticket_status') not in (None, '', 'unknown') and old_source not in AUTO_SOURCES:
        return False
    payload = {
        'ticket_status': state, 'ticket_status_verified_at': checked,
        'ticket_status_source': source, 'ticket_status_note': note[:180],
    }
    changed = any(event.get(k) != v for k, v in payload.items())
    event.update(payload)
    return changed


def clear_outdated_auto_status(event, now=None):
    """Remove past verified inventory when it outlives its TTL."""
    source = event.get('ticket_status_source')
    status = event.get('ticket_status')
    if source not in AUTO_SOURCES or status not in STATUS_TTLS_HOURS:
        return False
    if not stale(event.get('ticket_status_verified_at'), STATUS_TTLS_HOURS[status], now):
        return False
    for key in ('ticket_status', 'ticket_status_source', 'ticket_status_verified_at', 'ticket_status_note'):
        event.pop(key, None)
    return True


def tm_phase(data, now=None):
    """Status of PUBLIC SALES, never a guarantee of remaining tickets."""
    if not isinstance(data, dict):
        return None
    code = str((data.get('dates', {}).get('status') or {}).get('code', '')).lower()
    if code in ('canceled', 'cancelled', 'postponed', 'rescheduled'):
        return 'paused'
    public = (data.get('sales') or {}).get('public') or {}
    start = parse_dt(public.get('startDateTime'))
    end = parse_dt(public.get('endDateTime'))
    t = now or NOW()
    if start and t < start:
        return 'upcoming'
    if end and t >= end:
        return 'closed'
    if code == 'onsale' and (not start or t >= start) and (not end or t < end):
        return 'on_sale'
    # 'offsale' can be before sale or after sale, NOT proof of sold out.
    return None


def tm_price_ranges(data):
    """Discovery API priceRanges: advertised range (not necessarily seats remaining)."""
    vals = []
    for row in (data.get('priceRanges') or []):
        if not isinstance(row, dict) or str(row.get('currency', '')).upper() != 'CZK':
            continue
        if str(row.get('type', 'standard')).lower() not in ('standard', ''):
            continue
        try:
            low, high = float(row['min']), float(row.get('max', row['min']))
        except (TypeError, ValueError, KeyError, OverflowError):
            continue
        if math.isfinite(low) and math.isfinite(high) and 0 < low <= high <= 200_000:
            vals.append((low, high))
    if not vals:
        return None
    return round(min(v[0] for v in vals)), round(max(v[1] for v in vals))


def valid_o2_url(url):
    parsed = urlparse(str(url))
    return parsed.scheme == 'https' and parsed.hostname in O2_DOMAINS and parsed.path.startswith('/events/')


def check_robots(url):
    parsed = urlparse(url)
    origin = f'{parsed.scheme}://{parsed.netloc}'
    try:
        robots = SESSION.get(origin + '/robots.txt', timeout=12)
        if robots.status_code != 200:
            return False
        rp = RobotFileParser()
        rp.parse(robots.text.splitlines())
        return rp.can_fetch(UA, url)
    except requests.RequestException:
        return False


def _flat(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip().casefold()


def official_o2_status(html):
    """Only use explicit CURRENT labels/status cells, not mentions in body/old reviews.

    O2 can say that a public sale is running but this does not prove remaining
    stock. We report this separately as 'sales_phase', never 'available'.
    """
    soup = BeautifulSoup(html, 'html.parser')
    for t in soup.select('script,style,noscript'):
        t.decompose()
    heading = soup.find('h1')
    labels=[]
    if heading:
        # O2 event landing page shows the ticket CTA/status close to its h1.
        # Related events elsewhere on the page must not affect THIS event.
        fragments=list(soup.stripped_strings)
        title=_flat(heading.get_text(' ', strip=True))
        offsets=[i for i, fragment in enumerate(fragments) if _flat(fragment)==title]
        if offsets:
            idx=offsets[0]
            nearby=fragments[max(0,idx-6):idx+15]
            for fragment in nearby:
                txt=_flat(fragment)
                if re.fullmatch(r'(?:vyprod[aá]no|sold[ -]?out)\s*!*',txt):
                    labels.append('sold_out')
                elif re.fullmatch(r'(?:posledn[ií]\s+(?:vstupenky|m[ií]sta|l[ií]stky)|zb[yý]v[aá]\s+(?:jen\s+)?p[aá]r\s+(?:vstupenek|m[ií]st))\s*!*',txt):
                    labels.append('low')
                elif re.fullmatch(r'(?:do[cč]asn[eě]\s+vyprod[aá]no|moment[aá]ln[eě]\s+vyprod[aá]no)\s*!*',txt):
                    labels.append('temporarily_sold_out')
    # Look for current sale reservation cell, not 'popis' or related concerts.
    sale_phase = None
    for textnode in soup.find_all(string=True):
        if _flat(textnode) in {'prodej / rezervace', 'prodej/rezervace'}:
            parent = textnode.parent
            if not parent:
                continue
            sibling = parent.find_next_sibling()
            text = _flat(sibling.get_text(' ', strip=True)) if sibling else ''
            if not text and parent.parent:
                pieces = list(parent.parent.stripped_strings)
                if len(pieces) > 1:
                    text = _flat(' '.join(pieces[1:]))
            if 'právě probíhá' in text or 'prodej vstupenek probíhá' in text:
                sale_phase = 'on_sale'
            elif 'prodej vstupenek byl ukončen' in text:
                sale_phase = 'closed'
            break
    state = 'temporarily_sold_out' if 'temporarily_sold_out' in labels else (
        'sold_out' if 'sold_out' in labels else 'low' if 'low' in labels else None
    )
    return state, sale_phase


def read_json_response(resp):
    try:
        return resp.json()
    except ValueError:
        return None


def enrich_tm_details(events, api_key, checked, now):
    if not api_key:
        print('TM Discovery: chybí API klíč, fáze prodeje se nedá ověřit')
        return 0
    eligible = [e for e in events if str(e.get('id', '')).startswith('ticketmaster-')
                and stale(e.get('sales_phase_checked_at'), 18, now)]
    eligible.sort(key=lambda e: (e.get('sales_phase_checked_at') or '', e.get('date', '9999')))
    checked_count=phases=prices=0
    started = time.monotonic()
    for event in eligible[:DETAIL_LIMIT]:
        if time.monotonic()-started > 140: break
        eid = str(event['id']).removeprefix('ticketmaster-')
        if not re.fullmatch(r'[A-Za-z0-9_-]{3,80}', eid):
            continue
        try:
            response = SESSION.get(TM_DETAIL.format(id=eid),
                                   params={'apikey': api_key}, timeout=16)
            if response.status_code != 200:
                print(f'TM Discovery detail: HTTP {response.status_code} (bez změn)')
                continue
            data = read_json_response(response)
            if not isinstance(data, dict):
                continue
        except requests.RequestException as exc:
            print('TM Discovery detail: síťová chyba', type(exc).__name__)
            continue
        checked_count += 1
        phase = tm_phase(data, now)
        event['sales_phase_checked_at'] = checked
        event['sales_phase_source'] = 'Ticketmaster Discovery API'
        if phase:
            if event.get('sales_phase') != phase:
                phases += 1
            event['sales_phase'] = phase
        else:
            event.pop('sales_phase', None)
        rng = tm_price_ranges(data)
        if rng and phase not in ('paused','closed') and safe_price_update(event, *rng, 'Ticketmaster', checked):
            prices += 1
        time.sleep(0.15)
    print(f'TM Discovery: {checked_count} detailů, {phases} změn fáze prodeje, {prices} doplněných cen')
    return checked_count


def enrich_o2(events, checked, now):
    eligible = [e for e in events if valid_o2_url(e.get('ticket_url', ''))
                and stale(e.get('sales_phase_checked_at'), 16, now)]
    eligible.sort(key=lambda e: (e.get('sales_phase_checked_at') or '', e.get('date', '9999')))
    used=states=phases=0
    started = time.monotonic()
    url_dates={}
    for e in events:
        u=e.get('ticket_url','')
        if valid_o2_url(u): url_dates.setdefault(u,set()).add(e.get('date'))
    robots_cache={}
    for event in eligible[:O2_LIMIT]:
        if time.monotonic()-started > 120: break
        url = event['ticket_url']
        host = urlparse(url).hostname
        if host not in robots_cache:
            robots_cache[host] = check_robots(url)
        if not robots_cache[host]:
            print('O2: web nepovolil automatickou kontrolu pro', host)
            continue
        try:
            response = SESSION.get(url, timeout=14)
            if response.status_code != 200 or len(response.content) > 3_000_000:
                continue
            state, phase = official_o2_status(response.text)
        except requests.RequestException:
            continue
        used += 1
        event['sales_phase_checked_at'] = checked
        event['sales_phase_source'] = 'O2 official'
        if phase:
            event['sales_phase'] = phase
            phases += 1
        # A multi-date landing page may mention sold-out only for ONE show;
        # without date-specific evidence never mark every date as sold out.
        if len(url_dates.get(url,set()))>1: state=None
        if state and update_availability(event, state, 'O2 official', checked,
                                          'Výslovné označení na stránce pořadatele.'):
            states += 1
        time.sleep(0.45)
    print(f'O2: {used} detailů, {phases} fází prodeje, {states} potvrzených dostupností')
    return used


def enrich_inventory(events, key, checked, now):
    if not key:
        print('TM Inventory: NENÍ PŘIPOJENO – nutný schválený klíč pro stav míst a skutečné ceny')
        return 0
    valid = [e for e in events if str(e.get('id', '')).startswith('ticketmaster-')
             and (e.get('ticket_status_source') not in AUTO_SOURCES or
                  stale(e.get('ticket_status_verified_at'), 10, now))]
    # Iterate stale statuses first, then oldest checks; keep 350 events within 24h at 30/h.
    valid.sort(key=lambda e: (e.get('ticket_status_verified_at') or '', e.get('date', '9999')))
    checked_count=updated=prices=0
    started = time.monotonic()
    for event in valid[:INVENTORY_LIMIT]:
        if time.monotonic()-started > 140: break
        eid = str(event['id']).removeprefix('ticketmaster-')
        if not re.fullmatch(r'[A-Za-z0-9_-]{3,80}', eid):
            continue
        try:
            res = SESSION.post(TM_INVENTORY, params={'events': eid, 'apikey': key}, timeout=13)
            if res.status_code in (401, 403):
                print('TM Inventory: NEMÁŠ PŘÍSTUP (HTTP %d), bez změny stavů.' % res.status_code)
                break
            if res.status_code != 200:
                print('TM Inventory: HTTP %d; tento záznam přeskočen.' % res.status_code)
                continue
            payload = read_json_response(res)
            if not isinstance(payload, list):
                continue
            row = next((r for r in payload if isinstance(r, dict)
                        and str(r.get('eventId') or r.get('eventid') or '') == eid), None)
            if not row:
                continue
        except requests.RequestException as exc:
            print('TM Inventory: chyba připojení', type(exc).__name__)
            continue
        checked_count += 1
        state = inventory_state(row)
        # TICKETS_NOT_AVAILABLE means unavailable *through primary channels*,
        # not proof of an event being permanently sold out.
        if state == 'temporarily_sold_out':
            if event.get('sales_phase') != 'on_sale':
                # Could be presale / paused / future. Do not label sold out.
                state = None
        if state and update_availability(event, state, 'Ticketmaster Inventory Status API', checked,
                                         'Ověřeno pro primární prodej; další kanály mohou mít jiné nabídky.'):
            updated += 1
        rng = inventory_price(row)
        if rng and safe_price_update(event, *rng, 'Ticketmaster Inventory Status API', checked):
            prices += 1
        # Record last successful inventory check even if unknown, without creating a false status.
        event['inventory_checked_at'] = checked
        time.sleep(0.12)
    print(f'TM Inventory: {checked_count} ověřeno, {updated} stavů, {prices} cen')
    return checked_count



def normalize_name(value):
    import unicodedata
    x = unicodedata.normalize('NFKD', str(value or '').casefold())
    return re.sub(r'[^a-z0-9]+', '', ''.join(c for c in x if not unicodedata.combining(c)))


def matching_o2_show(a, b):
    # Must match the SAME date + venue; skip ticket extras (Fast Track, parking ...).
    if a.get('date') != b.get('date') or a.get('date') is None:
        return False
    if normalize_name(a.get('venue')) != normalize_name(b.get('venue')):
        return False
    if not valid_o2_url(b.get('ticket_url', '')):
        return False
    if re.search(r'fast\s*track|early\s*entry|upgrade|parking|meet\s*&\s*greet|vip',
                 str(a.get('title', '')), flags=re.I):
        return False
    na, nb = normalize_name(a.get('title')), normalize_name(b.get('title'))
    if not na or not nb:
        return False
    if na == nb:
        return True
    short, long = sorted((na, nb), key=len)
    if len(short) >= 8 and short in long and len(short) / len(long) >= 0.23:
        return True
    return min(len(na), len(nb)) >= 10 and SequenceMatcher(None,na,nb).ratio() > .87


def crossfill_official_prices(events, checked):
    """Free fallback: official O2 ticket prices for matching Ticketmaster records.

    It never assumes similar concerts at different venues/dates are the same.
    """
    official=[e for e in events if valid_o2_url(e.get('ticket_url', ''))
              and isinstance(e.get('price'), (int,float)) and e['price'] >= 0]
    changes=0
    for event in events:
        if not str(event.get('id','')).startswith('ticketmaster-') or event.get('price') is not None:
            continue
        matches=[x for x in official if matching_o2_show(event,x)]
        if len(matches)!=1:
            continue  # avoid ambiguity and cross-venue duplicates
        other=matches[0]
        event.update({'price':other['price'], 'price_max':other.get('price_max'),
                      'price_source':str(other.get('source') or 'O2 official')+' (stejná akce)',
                      'price_from':True,'price_checked_at':checked[:10]})
        changes+=1
    print(f'CENY O2 → Ticketmaster: {changes} bezpecne sparovanych cen')
    return changes

def sync(events, now=None, tm_key='', inv_key=''):
    now = now or NOW()
    checked = timestamp(now)
    cleared = sum(clear_outdated_auto_status(e, now) for e in events)
    if cleared:
        print(f'Dostupnost: {cleared} zastaralých stavů změněno na neověřeno')
    enrich_tm_details(events, tm_key, checked, now)
    enrich_o2(events, checked, now)
    crossfill_official_prices(events, checked)
    enrich_inventory(events, inv_key, checked, now)
    return events


def main():
    data = json.loads(EVENT_FILE.read_text('utf-8'))
    events = data.get('events')
    if not isinstance(events, list):
        raise RuntimeError('events.json: není pole events')
    before = json.dumps(events, ensure_ascii=False, sort_keys=True)
    sync(events, tm_key=os.getenv('TICKETMASTER_API_KEY', '').strip(),
         inv_key=os.getenv('TICKETMASTER_INVENTORY_API_KEY', '').strip())
    if json.dumps(events, ensure_ascii=False, sort_keys=True) != before:
        data['updated_at'] = datetime.now(ZoneInfo('Europe/Prague')).isoformat(timespec='seconds')
        EVENT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('UKA: ceny a prodejní stavy aktualizovány')
    else:
        print('UKA: žádné ověřené změny')
    return 0


if __name__ == '__main__':
    sys.exit(main())
