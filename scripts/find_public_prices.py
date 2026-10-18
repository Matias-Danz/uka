#!/usr/bin/env python3
"""UKA: carefully enrich missing CZK prices from public event details.

No access to a Ticketmaster seat map is attempted. Website robots directives
are respected, including 403/unavailable robots (fail closed). This updater
only reads linked/explicitly indexed event pages and does not claim to
know live ticket inventory. It never overwrites a nonempty price.

Run AFTER update_events.py and sync_ticket_info.py:
    python scripts/find_public_prices.py
    python scripts/find_public_prices.py --dry-run

Optional price_links.json contains additional *confirmed event detail links*.
Rotating public GoOut catalogue pages are inspected automatically to avoid
entering hundreds of URLs by hand. Coverage is partial and best-effort.
Such links are matched to events by title, exact date and venue. The script
also tries event's own ticket_url when on the supported public sites.
"""
from __future__ import annotations
import argparse
import base64
import json
import re
import sys
import time
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse, urljoin, urlencode
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
EVENTS_FILE = ROOT / 'events.json'
LINKS_FILE = ROOT / 'price_links.json'
REPORT_FILE = ROOT / 'price_check_report.json'
USER_AGENT = 'UKA-EventPriceChecker/1.0 (public event metadata, respectful robots.txt)'
HEADERS = {'User-Agent': USER_AGENT, 'Accept-Language': 'cs-CZ,cs;q=0.9'}
SUPPORTED_HOSTS = {'goout.net', 'www.goout.net', 'eventlook.cz', 'www.eventlook.cz',
                   'www.o2arena.cz', 'www.o2universum.cz'}
NO_PRICE_HOSTS = {'ticketmaster.cz', 'www.ticketmaster.cz', 'app.ticketmaster.com'}
MAX_REQUESTS = 18
MAX_SECONDS = 110
MAX_BYTES = 2_000_000
MAX_AGE_DAYS = 7
CATALOG_PAGES_PER_RUN = 4  # modest load: up to 4 public listings + up to 14 event details
GOOUT_CATALOGS = {
    'Praha': 'https://goout.net/cs/praha/koncerty/leznyvlkkzf/',
    'Brno': 'https://goout.net/cs/brno/koncerty/lezjyvlkkzf/',
    'Ostrava': 'https://goout.net/cs/ostrava/koncerty/lezaawlkkzf/',
    'Plzeň': 'https://goout.net/cs/plzen/koncerty/lezlyvlkkzf/',
}
DATE_RE = re.compile(r'(?<!\d)([0-3]?\d)\.\s*([01]?\d)\.\s*(20\d{2})(?!\d)')
MONEY_RE = re.compile(r'(?<!\d)(\d{1,3}(?:[ \u00a0\u202f.]\d{3})*|\d{1,6})\s*(?:Kč|CZK)(?!\w)', re.I)
RANGE_RE = re.compile(r'(?:od\s+)?([\d .\u00a0\u202f]+)\s*(?:Kč|CZK)?\s*[\-–—]\s*([\d .\u00a0\u202f]+)\s*(?:Kč|CZK)', re.I)
LABELS = {'vstupné', 'vstupne', 'cena vstupenek', 'cena vstupenky', 'vstupné od', 'tickets from', 'ticket price', 'price', 'entry', 'admission', 'cena', 'cena od'}
NEGATIVE_TITLES = re.compile(r'\b(parking|fast track|early entry|upgrade|meet and greet|merch|balicek)\b', re.I)


def norm(s):
    x = unicodedata.normalize('NFKD', str(s or '').casefold())
    x = ''.join(ch for ch in x if not unicodedata.combining(ch))
    return re.sub(r'[^a-z0-9]+', ' ', x).strip()


def host_ok(url):
    p = urlparse(str(url or ''))
    return p.scheme == 'https' and p.hostname in SUPPORTED_HOSTS and not p.username and not p.password


def parse_price(val, *, labeled=False):
    """Accept CZK only, or a bare amount/range immediately after an Entry label.

    The 2nd case is used by GoOut (e.g. Entry / 690–3790). It is NOT
    applied to unrelated body text or to other currencies.
    """
    if val is None:
        return None
    raw = ' '.join(str(val).replace('\u00a0', ' ').replace('\u202f', ' ').split()).strip()
    if not raw or len(raw) > 85:
        return None
    if norm(raw) in {'zdarma', 'vstup zdarma', 'vstupne zdarma', 'free entry'}:
        return (0, 0)
    # CZK 690, 690 Kč, 790–990, 790 - 990 CZK, CZK 1,190.00
    prefix = re.match(r'^(?:CZK|Kč)\s*', raw, flags=re.I)
    suffix = re.search(r'\s*(?:CZK|Kč)$', raw, flags=re.I)
    currency = bool(prefix or suffix)
    if not currency and not labeled:
        return None
    clean = raw
    if prefix: clean = clean[prefix.end():]
    clean = re.sub(r'\s*(?:CZK|Kč)$', '', clean, flags=re.I).strip()
    if not re.fullmatch(r'[0-9\s.,–—-]+', clean):
        return None

    def amount(part):
        part = re.sub(r'\s+', '', part)
        if re.fullmatch(r'\d{1,3}(?:[.,]\d{3})+', part):
            value = int(re.sub(r'[.,]', '', part))
        elif re.fullmatch(r'\d+[.,]00', part):
            value = int(part[:-3])
        elif part.isdigit():
            value = int(part)
        else:
            return None
        return value if 0 < value <= 100000 else None

    parts = re.split(r'\s*[-–—]\s*', clean)
    if len(parts) == 1:
        value = amount(parts[0])
        return (value, None) if value is not None else None
    if len(parts) == 2:
        low, high = amount(parts[0]), amount(parts[1])
        return (low, high) if low is not None and high is not None and low <= high else None
    return None


def structured_events(soup):
    def walk(obj):
        if isinstance(obj, list):
            for row in obj: yield from walk(row)
        elif isinstance(obj, dict):
            if '@graph' in obj:
                yield from walk(obj['@graph'])
            raw = obj.get('@type', [])
            types = [raw] if isinstance(raw, str) else raw if isinstance(raw, list) else []
            if any(str(t).lower().endswith('event') for t in types):
                yield obj
    for node in soup.select('script[type="application/ld+json"]'):
        try:
            yield from walk(json.loads(node.string or node.get_text()))
        except (ValueError, TypeError):
            continue


def structured_price(event):
    offers = event.get('offers', [])
    if isinstance(offers, dict): offers = [offers]
    found = []
    for offer in offers if isinstance(offers, list) else []:
        if not isinstance(offer, dict): continue
        curr = offer.get('priceCurrency', '')
        if str(curr).upper() != 'CZK': continue
        raw_low = offer.get('lowPrice', offer.get('price'))
        raw_high = offer.get('highPrice')
        try:
            low = round(float(str(raw_low).replace(' ', '').replace(',', '.')))
            high = round(float(str(raw_high).replace(' ', '').replace(',', '.'))) if raw_high is not None else None
        except (TypeError, ValueError, OverflowError):
            continue
        if 0 < low <= 100000 and (high is None or low <= high <= 100000):
            found.append((low, high))
    if not found: return None
    return min(p[0] for p in found), max((p[1] or p[0]) for p in found)


def label_value(soup):
    """Prices immediately after a price heading, not from arbitrary prose."""
    strings = [str(x).strip() for x in soup.stripped_strings]
    for i, txt in enumerate(strings):
        if norm(txt).rstrip(':') not in LABELS:
            continue
        # Labels 'Entry' and 'Vstupné' are sufficient context for bare numbers.
        for candidate in strings[i+1:i+4]:
            if len(candidate) > 85 or norm(candidate) in LABELS:
                break
            price = parse_price(candidate, labeled=True)
            if price is not None:
                return price
    return None


def iso_day(raw):
    if not raw: return None
    s = str(raw)
    try:
        return date.fromisoformat(s[:10]).isoformat()
    except ValueError: pass
    m = DATE_RE.search(s) or re.search(r'(?<!\d)([0-3]?\d)[/-]([01]?\d)[/-](20\d{2})(?!\d)', s)
    if m:
        try: return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError: pass
    return None


def labeled_text(soup, label):
    strings = list(soup.stripped_strings)
    for i, fragment in enumerate(strings):
        if norm(fragment).strip(':') == norm(label) and i+1 < len(strings):
            return str(strings[i+1]).strip()[:150]
    return ''


def extract_page(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    events = list(structured_events(soup))
    title_node = soup.find('h1')
    title = title_node.get_text(' ', strip=True) if title_node else ''
    event_date = None
    venue = ''
    price = None
    for obj in events:
        title = str(obj.get('name') or title)
        event_date = iso_day(obj.get('startDate')) or event_date
        place = obj.get('location')
        if isinstance(place, list): place = next((x for x in place if isinstance(x, dict)), {})
        if isinstance(place, dict): venue = str(place.get('name') or venue)
        price = structured_price(obj) or price
    # Extract an HTML time tag before any prose/date in unrelated articles.
    if not event_date:
        time_node = soup.select_one('time[datetime]')
        if time_node: event_date = iso_day(time_node.get('datetime'))
    # Visible event header first; do not interpret a date in an unrelated story.
    if not event_date:
        container = soup.find('main') or soup.find('article') or soup.body or soup
        short = ' '.join(list(container.stripped_strings)[:42])
        event_date = iso_day(short)
    if not venue:
        venue = labeled_text(soup, 'Místo') or labeled_text(soup, 'Venue')
    price = price or label_value(soup)
    # Safe optional html data attribute, if marked with CZK explicitly.
    if price is None:
        for node in soup.select('[itemprop="price"][content],meta[property="product:price:amount"][content]'):
            tag = node.parent
            raw = node.get('content')
            try: candidate = int(round(float(str(raw).replace(',', '.'))))
            except (ValueError, TypeError): continue
            if candidate <= 0 or candidate > 100000: continue
            currency_node = soup.select_one('[itemprop="priceCurrency"][content]')
            if currency_node and currency_node.get('content', '').upper() == 'CZK':
                price = (candidate, None); break
    return {'title': title, 'date': event_date, 'venue': venue, 'price': price, 'url': url}


def same_event(event, detail):
    """Exact date + venue + title/artist identity, with conservative aliases."""
    if event.get('date') != detail.get('date') or not detail.get('date'):
        return False
    a, b = norm(event.get('venue')), norm(detail.get('venue'))
    if not a or not b:
        return False
    venue_aliases = {'o2 arena': 'o2 arena', '02 arena': 'o2 arena',
                     'o2 universum': 'o2 universum', 'areal 7': 'areal 7',
                     'prague congress centre': 'kongresove centrum praha',
                     'kongresove centrum praha': 'kongresove centrum praha'}
    a, b = venue_aliases.get(a, a), venue_aliases.get(b, b)
    if a != b and SequenceMatcher(None, a, b).ratio() < .89:
        return False
    if NEGATIVE_TITLES.search(str(event.get('title', ''))):
        return False
    title = norm(event.get('title'))
    page = norm(detail.get('title'))
    artist = norm(event.get('artist'))
    if not title or not page:
        return False
    if title == page or SequenceMatcher(None, title, page).ratio() >= .79:
        return True
    # Artist alone only when it's a reasonably specific standalone name,
    # and title differs merely by a descriptive suffix (e.g. tour name).
    if artist and len(artist) >= 8 and page == artist and (artist in title or title in artist):
        return True
    # Allow descriptive tour/support terms when artist/leading title remains intact,
    # provided the date and venue have already matched exactly.
    def meaningful_tokens(raw):
        ignored = {'tour', 'support', 'with', 'and', 'the', 'live', 'world', '2026', '2027'}
        return {t for t in norm(raw).split() if len(t) >= 3 and t not in ignored}
    ta, tb = meaningful_tokens(title), meaningful_tokens(page)
    if ta and tb:
        overlap = ta & tb
        if len(overlap) >= 2 and len(overlap) / min(len(ta), len(tb)) >= .7:
            return True
        if len(ta) == 1 and ta <= tb and len(next(iter(ta))) >= 5:
            return True
        if len(tb) == 1 and tb <= ta and len(next(iter(tb))) >= 5:
            return True
    return False


class RespectfulFetcher:
    def __init__(self, session=None):
        self.session = session or requests.Session()
        self.session.headers.update(HEADERS)
        self.robots = {}
        self.count = 0

    def allowed(self, url):
        if not host_ok(url): return False
        p = urlparse(url)
        host = p.hostname
        if host not in self.robots:
            try:
                resp = self.session.get(f'https://{host}/robots.txt', timeout=8, allow_redirects=False)
                if resp.status_code != 200 or len(resp.content) > 250000:
                    self.robots[host] = None
                else:
                    r = RobotFileParser()
                    r.parse(resp.text.splitlines())
                    self.robots[host] = r
            except requests.RequestException:
                self.robots[host] = None
        parser = self.robots[host]
        return bool(parser and parser.can_fetch(USER_AGENT, url))

    def get_html(self, url):
        if self.count >= MAX_REQUESTS or not self.allowed(url): return None, 'robots/unavailable'
        try:
            self.count += 1
            r = self.session.get(url, timeout=15, allow_redirects=False)
            if r.status_code in {301, 302, 303, 307, 308}:
                loc = urljoin(url, r.headers.get('Location', ''))
                if not self.allowed(loc): return None, 'redirect disallowed'
                self.count += 1
                r = self.session.get(loc, timeout=15, allow_redirects=False)
            if r.status_code != 200 or len(r.content) > MAX_BYTES:
                return None, f'HTTP {r.status_code}'
            if 'html' not in r.headers.get('Content-Type', 'text/html'):
                return None, 'not HTML'
            return r.text, None
        except requests.RequestException as exc:
            return None, type(exc).__name__

    def get(self, url):
        html, error = self.get_html(url)
        return (extract_page(html, url), None) if html else (None, error)


def city_key(value):
    value = norm(value)
    # Ticketmaster writes Czech municipal districts as Praha 1, Praha 9, etc.
    if re.fullmatch(r'praha(?: [1-9][0-9]?)?', value):
        return 'praha'
    return value


def goout_listing_url(city, *, sort='recommendations', page=0):
    """Build a PUBLIC GoOut page URL (no undocumented JSON endpoint).

    The public site exposes scrollId in links for ordinary catalogue paging.
    If a site changes that scheme, requests may return the first page or no
    useful items; this remains best-effort and fails safely.
    """
    base = GOOUT_CATALOGS[city]
    params = {'sort': sort}
    if page:
        cursor = base64.urlsafe_b64encode(
            json.dumps({'donutSize': 'd0', 'page': page}, separators=(',', ':')).encode()
        ).decode().rstrip('=')
        params['scrollId'] = cursor
    return base + '?' + urlencode(params)


def catalogue_plan(now):
    """Rotate through publicly accessible catalogue pages each hour.

    No account, search API key or manual per-event price_links.json is needed.
    We intentionally bound traffic. Across 24 hours different pages are
    visited; each run processes only a small slice.
    """
    hour_number = int(now.timestamp() // 3600)
    smaller = ['Brno', 'Ostrava', 'Plzeň']
    # New/popular events appear early; future shows may appear much deeper.
    # Two different recommendation pages reach additional dates over time.
    return [
        ('Praha', 'recommendations', hour_number % 36 + 1),
        ('Praha', 'recommendations', (hour_number * 7 + 11) % 36 + 1),
        ('Praha', 'popularity' if hour_number % 2 else 'news', 0),
        (smaller[hour_number % 3], 'recommendations', (hour_number // 3) % 20 + 1),
    ]


def plausible_identity(a, b):
    """Candidate-title match ONLY; verified exact date+venue in same_event."""
    a, b = norm(a), norm(b)
    if not a or not b or len(b) < 5: return False
    if a == b or SequenceMatcher(None, a, b).ratio() >= .71: return True
    def important(t):
        ignored = {'tour', 'support', 'world', 'live', 'prague', 'praha', '2026', '2027',
                   '2028', 'europe', 'the', 'and', 'with', 'special', 'guest', 'hoste'}
        return {w for w in t.split() if len(w) >= 4 and w not in ignored}
    aa, bb = important(a), important(b)
    shared = aa & bb
    return bool(shared and (len(shared) >= 2 or any(len(w) >= 7 for w in shared))
                and len(shared) / min(len(aa), len(bb)) >= .65)


def discover_goout(events, fetcher, now=None):
    """Discover public GoOut EVENT urls from rotated catalogue pages.

    This is NOT a generic internet search. Public programme pages only list
    part of GoOut's catalogue and not all events on Ticketmaster. NEVER claim
    complete coverage. Candidate URLs must pass same_event before writing.
    """
    now = now or datetime.now(timezone.utc)
    by_city = defaultdict(list)
    for ev in events:
        if not NEGATIVE_TITLES.search(str(ev.get('title', ''))):
            by_city[city_key(ev.get('city'))].append(ev)
    links = defaultdict(list)
    stats = {'pages': 0, 'candidates': 0}
    for city, sort, page in catalogue_plan(now)[:CATALOG_PAGES_PER_RUN]:
        key = city_key(city)
        if not by_city.get(key): continue
        url = goout_listing_url(city, sort=sort, page=page)
        html, error = fetcher.get_html(url)
        if error:
            print(f'GOOUT KATALOG: {city}, {sort} str.{page}: nedostupný ({error})')
            continue
        stats['pages'] += 1
        soup = BeautifulSoup(html, 'html.parser')
        count = 0
        seen = set()
        for a in soup.select('a[href]'):
            raw_link = a.get('href', '')
            event_url = urljoin(url, raw_link)
            # GoOut exposes event detail links as /cs/slug/szID or /en/slug/szID.
            if not host_ok(event_url) or not re.fullmatch(
                r'/(?:cs|en)/[^/]+/sz[a-z0-9]+/?', urlparse(event_url).path, re.I
            ): continue
            if event_url in seen: continue
            seen.add(event_url)
            page_title = a.get_text(' ', strip=True)
            if not page_title.strip(): continue
            for ev in by_city[key]:
                if not (plausible_identity(ev.get('title'), page_title)
                        or plausible_identity(ev.get('artist'), page_title)):
                    continue
                if event_url not in links[ev['id']]:
                    links[ev['id']].append(event_url)
                    count += 1
        stats['candidates'] += count
        print(f'GOOUT KATALOG: {city}, {sort} str.{page}: {count} kandidátů, '
              f'{len(seen)} odkazů na akce; detail následně ověří datum a místo')
        time.sleep(.3)
    print(f'GOOUT KATALOG CELKEM: {stats["pages"]} stran, '
          f'{stats["candidates"]} předběžných shod (nejsou to zatím potvrzené ceny)')
    return links


def load_seeds():
    if not LINKS_FILE.exists():
        return []
    obj = json.loads(LINKS_FILE.read_text('utf-8'))
    if not isinstance(obj, list):
        raise RuntimeError('price_links.json musí být JSON pole v hranatých závorkách []')
    return [x for x in obj if isinstance(x, dict) and host_ok(x.get('url'))]


def seed_matches(event, seed):
    if event.get('date') != seed.get('date'):
        return False
    if seed.get('event_id'):
        # Event ID is exact, but also check venue/date/title to prevent stale ID mistakes.
        return (event.get('id') == seed['event_id']
                and norm(event.get('venue')) == norm(seed.get('venue'))
                and norm(event.get('title')) == norm(seed.get('title')))
    a, b = norm(event.get('title')), norm(seed.get('title'))
    art = norm(event.get('artist'))
    return bool(a and b and (a == b or SequenceMatcher(None, a, b).ratio() >= .78
                             or (art and len(art) >= 8 and art == b)))


def seed_event_candidates(event, seeds):
    for seed in seeds:
        if seed_matches(event, seed):
            yield seed['url']


def observed_seed_price(event, seed, today):
    """A human-verified source observation, not live inventory.

    Fallback only if exact event/date/venue/title ID matched, source is provided,
    observed date is recent, and amounts were independently verified.
    """
    if not seed_matches(event, seed) or not seed.get('event_id'):
        return None
    day_str = seed.get('observed_at')
    if not day_str or not seed.get('observed_source'):
        return None
    try:
        day = date.fromisoformat(day_str)
    except ValueError:
        return None
    if not (0 <= (today-day).days <= 5):
        return None
    low, high = seed.get('observed_price'), seed.get('observed_price_max')
    if isinstance(low, bool) or not isinstance(low, int) or not (0 < low <= 100000):
        return None
    if high is not None and (isinstance(high, bool) or not isinstance(high, int) or not low <= high <= 100000):
        return None
    return low, high


def process(events, fetcher, seeds, now=None):
    now = now or datetime.now(timezone.utc)
    started = time.monotonic()
    today = now.date().isoformat()
    upcoming = [e for e in events if e.get('price') is None and e.get('date', '') >= today]
    upcoming.sort(key=lambda e: (e.get('public_price_attempt_at', ''), e.get('date', '9999')))
    report = {'unknown_before': len(upcoming), 'matched': [], 'skipped': defaultdict(int),
              'checked': 0, 'price_sources': defaultdict(int), 'seed_targets': 0}
    details_cache = {}
    catalog_urls = discover_goout(upcoming, fetcher, now=now)
    observed_by_id = defaultdict(list)
    for seed in seeds:
        if seed.get('event_id'):
            observed_by_id[seed['event_id']].append(seed)
    report['seed_targets'] = sum(any(seed_matches(ev, x) for x in observed_by_id.get(ev.get('id'), [])) for ev in upcoming)
    for event in upcoming:
        if fetcher.count >= MAX_REQUESTS or time.monotonic() - started > MAX_SECONDS:
            break
        old = event.get('public_price_attempt_at', '')
        try:
            if old and date.fromisoformat(old) + timedelta(days=MAX_AGE_DAYS) > now.date():
                # Still allow a newly supplied verified source observation.
                if not any(observed_seed_price(event, x, now.date()) for x in observed_by_id.get(event.get('id'), [])):
                    continue
        except ValueError:
            pass
        urls = []
        for key in ('price_url', 'ticket_url', 'source_url'):
            url = event.get(key, '')
            if host_ok(url) and url not in urls:
                urls.append(url)
        for url in seed_event_candidates(event, seeds):
            if url not in urls:
                urls.append(url)
        for url in catalog_urls.get(event.get('id'), []):
            if url not in urls:
                urls.append(url)
        if not urls:
            continue
        event['public_price_attempt_at'] = today
        for url in urls[:3]:
            seed = next((s for s in seeds if s.get('url') == url and seed_matches(event, s)), None)
            if url not in details_cache:
                details_cache[url] = fetcher.get(url)
                report['checked'] += 1
                time.sleep(.1)
            detail, error = details_cache[url]
            evidence_type = None
            price = None
            if error:
                report['skipped'][error] += 1
            elif not same_event(event, detail):
                report['skipped']['identity mismatch'] += 1
            elif detail['price'] is None:
                report['skipped']['no explicit CZK price'] += 1
            else:
                price = detail['price']
                evidence_type = 'živě načteno'
            if price is None and seed is not None:
                price = observed_seed_price(event, seed, now.date())
                if price is not None:
                    evidence_type = 'ověřený veřejný údaj (datum v price_links.json)'
            if price is None:
                continue
            low, high = price
            checked_at = today if evidence_type == 'živě načteno' else seed['observed_at']
            source = ('Veřejná stránka ' + urlparse(url).hostname if evidence_type == 'živě načteno'
                      else 'Ověřeno: ' + seed['observed_source'])
            event.update({'price': low, 'price_max': high,
                          'price_source': source,
                          'price_checked_at': checked_at,
                          'price_from': bool(high is not None and high > low),
                          'price_url': url})
            report['matched'].append({'id': event.get('id'), 'title': event.get('title'),
                                      'price': low, 'price_max': high, 'url': url,
                                      'type': evidence_type})
            report['price_sources'][evidence_type] += 1
            break
    report['skipped'] = dict(report['skipped'])
    report['price_sources'] = dict(report['price_sources'])
    report['unknown_after'] = sum(e.get('price') is None for e in events)
    report['requests'] = fetcher.count
    report['rotating_catalogues'] = len(catalogue_plan(now))
    report['index_matches'] = sum(len(v) for v in catalog_urls.values())
    return report


def run(dry_run=False):
    data = json.loads(EVENTS_FILE.read_text('utf-8'))
    events = data.get('events')
    if not isinstance(events, list): raise RuntimeError('events.json: očekávám {"events":[...]}')
    before = json.dumps(events, sort_keys=True, ensure_ascii=False)
    report = process(events, RespectfulFetcher(), load_seeds())
    print(f'VEŘEJNÉ CENY: {report["checked"]} detailů, {len(report["matched"])} nových cen, '
          f'{report["unknown_after"]} stále neznámých; {report["requests"]} HTML požadavků, '
          f'{report["index_matches"]} možných shod v katalozích')
    print(f'SHODA S ODKAZY: {report["seed_targets"]} akcí s chybějící cenou z aktuální databáze')
    for key, num in report['price_sources'].items(): print(f'  ZDROJ: {key}: {num}')
    for key, num in report['skipped'].items(): print(f'  Přeskočeno – {key}: {num}')
    for m in report['matched']:
        print('  NALEZENO:', m['title'], '=>', m['price'], 'Kč;', m['type'], '; zdroj:', m['url'])
    if dry_run:
        print('TESTOVACÍ REŽIM: events.json zůstává beze změny.')
        return report
    if json.dumps(events, sort_keys=True, ensure_ascii=False) != before:
        data['updated_at'] = datetime.now().astimezone().isoformat(timespec='seconds')
        EVENTS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    args = argparse.ArgumentParser(description='UKA: najdi spolehlivé ceny na veřejných eventových stránkách')
    args.add_argument('--dry-run', action='store_true', help='Bez zápisu do databáze')
    options = args.parse_args()
    try:
        run(options.dry_run)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print('CHYBA:', exc, file=sys.stderr)
        sys.exit(1)
