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
from zoneinfo import ZoneInfo
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
CACHE_FILE = ROOT / 'price_catalog_cache.json'
CACHE_TTL_DAYS = 45
MAX_CACHE_ITEMS = 3500
USER_AGENT = 'UKA-EventPriceChecker/1.0 (public event metadata, respectful robots.txt)'
HEADERS = {'User-Agent': USER_AGENT, 'Accept-Language': 'cs-CZ,cs;q=0.9'}
SUPPORTED_HOSTS = {'goout.net', 'www.goout.net', 'eventlook.cz', 'www.eventlook.cz',
                   'www.o2arena.cz', 'www.o2universum.cz'}
# Ticketmaster interactive checkout is deliberately not scraped: access is restricted.
MAX_REQUESTS = 24
MAX_SECONDS = 140
MAX_BYTES = 2_000_000
MAX_AGE_DAYS = 7  # per-URL cooldown, not per-event: new candidates get checked immediately
CATALOG_PAGES_PER_RUN = 8  # up to 8 public listings + remaining requests for matched event details
GOOUT_CATALOGS = {
    'Česko': 'https://goout.net/cs/cesko/koncerty/lezfymftizf/',
    'Praha': 'https://goout.net/cs/praha/koncerty/leznyvlkkzf/',
    'Brno': 'https://goout.net/cs/brno/koncerty/lezjyvlkkzf/',
    'Ostrava': 'https://goout.net/cs/ostrava/koncerty/lezaawlkkzf/',
    'Plzeň': 'https://goout.net/cs/plzen/koncerty/lezlyvlkkzf/',
}
DATE_RE = re.compile(r'(?<!\d)([0-3]?\d)\.\s*([01]?\d)\.\s*(20\d{2})(?!\d)')
MONEY_RE = re.compile(r'(?<!\d)(\d{1,3}(?:[ \u00a0\u202f.]\d{3})*|\d{1,6})\s*(?:Kč|CZK)(?!\w)', re.I)
RANGE_RE = re.compile(r'(?:od\s+)?([\d .\u00a0\u202f]+)\s*(?:Kč|CZK)?\s*[\-–—]\s*([\d .\u00a0\u202f]+)\s*(?:Kč|CZK)', re.I)
LABELS = {'vstupné', 'vstupne', 'cena vstupenek', 'cena vstupenky', 'vstupné od', 'tickets from', 'ticket price', 'price', 'entry', 'admission', 'cena', 'cena od'}
NEGATIVE_TITLES = re.compile(r'\b(parking|fast[ -]?track|early entry|upgrade|meet[ -]?and[ -]?greet|merch|balicek|vip upgrade|parking)\b', re.I)


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
        if re.fullmatch(r'\d{1,3}(?:,\d{3})+(?:\.00)?', part):
            value = int(part.split('.')[0].replace(',', ''))
        elif re.fullmatch(r'\d{1,3}(?:\.\d{3})+(?:,00)?', part):
            value = int(part.split(',')[0].replace('.', ''))
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
        normalized = norm(txt)
        # HTML often places the price in the SAME text node as the label.
        # Never treat an unrelated number in a description as a ticket price.
        if normalized not in LABELS:
            match = re.match(r'^\s*(vstupné|vstupne|entry|admission|price|cena vstupenek|cena)\s*[:：–-]\s*(.+)$', txt, re.I)
            if match:
                inline = parse_price(match.group(2), labeled=True)
                if inline is not None:
                    return inline
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
    city = ''
    price = None
    for obj in events:
        title = str(obj.get('name') or title)
        event_date = iso_day(obj.get('startDate')) or event_date
        place = obj.get('location')
        if isinstance(place, list): place = next((x for x in place if isinstance(x, dict)), {})
        if isinstance(place, dict):
            venue = str(place.get('name') or venue)
            address = place.get('address')
            if isinstance(address, dict):
                city = str(address.get('addressLocality') or city)
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
    return {'title': title, 'date': event_date, 'venue': venue, 'city': city, 'price': price, 'url': url}


def same_event(event, detail):
    """Exact date + venue + title/artist identity, with conservative aliases."""
    if event.get('date') != detail.get('date') or not detail.get('date'):
        return False
    a, b = norm(event.get('venue')), norm(detail.get('venue'))
    # A venue name can occur in several cities. When the source specifies a
    # city, require it to agree (Praha 7 and Praha are equivalent).
    if detail.get('city') and city_key(event.get('city')) != city_key(detail['city']):
        return False
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
    if re.fullmatch(r'(?:praha|prague)(?: [1-9][0-9]?)?', value):
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
    """Rotate allowed public HTML catalogue pages instead of retrying a few forever.

    Reading the whole public catalogue is not guaranteed: future event coverage
    remains partial. The persistent cache below allows *cumulative* discovery
    across hourly runs without re-requesting previously found event details.
    """
    hour = int(now.timestamp() // 3600)
    cities = ['Praha', 'Brno', 'Ostrava', 'Plzeň', 'Česko']
    sorts = ['popularity', 'recommendations', 'news']
    plan = [('Praha', 'popularity', 0), ('Česko', 'popularity', 0)]
    for offset in range(6):
        rotation = (hour * 6 + offset) % (len(cities) * len(sorts) * 18)
        city = cities[rotation % len(cities)]
        sort = sorts[(rotation // len(cities)) % len(sorts)]
        page = (rotation // (len(cities) * len(sorts))) % 18
        triple = (city, sort, page)
        if triple not in plan:
            plan.append(triple)
    return plan[:8]


def load_catalog_cache():
    """Cache contains candidate names/URLs, NEVER verified prices."""
    if not CACHE_FILE.exists():
        return {}
    try:
        raw = json.loads(CACHE_FILE.read_text(encoding='utf-8'))
        entries = raw.get('entries', {})
        if not isinstance(entries, dict):
            return {}
        today = datetime.now(ZoneInfo('Europe/Prague')).date()
        result = {}
        for url, entry in entries.items():
            if not host_ok(url) or urlparse(url).hostname not in {'goout.net', 'www.goout.net'}:
                continue
            if not isinstance(entry, dict) or not isinstance(entry.get('names'), list):
                continue
            seen = date.fromisoformat(entry.get('last_seen', '1970-01-01'))
            if 0 <= (today - seen).days <= CACHE_TTL_DAYS:
                result[url] = {'names': [str(n)[:160] for n in entry['names'][:8]],
                               'city': str(entry.get('city', 'Česko')),
                               'last_seen': seen.isoformat()}
        return result
    except (OSError, ValueError, TypeError, OverflowError):
        print('CACHE: poškozený soubor, bezpečně začínám s prázdnou pamětí')
        return {}


def persist_catalog_cache(entries):
    """Stable deterministic bounded cache to commit alongside events.json."""
    ordered = sorted(entries.items(), key=lambda item: (item[1]['last_seen'], item[0]), reverse=True)
    payload = {'version': 1, 'entries': dict(sorted(ordered[:MAX_CACHE_ITEMS]))}
    content = json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
    if not CACHE_FILE.exists() or CACHE_FILE.read_text('utf-8') != content:
        CACHE_FILE.write_text(content, encoding='utf-8')


def plausible_identity(a, b):
    """Candidate-title match ONLY; verified exact date+venue in same_event."""
    a, b = norm(a), norm(b)
    if not a or not b or len(b) < 5: return False
    if a == b or SequenceMatcher(None, a, b).ratio() >= .71: return True
    # E.g. 'FKJ' versus 'FKJ + support: Richie Griner'.
    # Date and venue are still mandatory when confirming the detail.
    if len(a) >= 3 and (b.startswith(a + ' ') or a.startswith(b + ' ') and len(b) >= 3):
        return True
    def important(t):
        ignored = {'tour', 'support', 'world', 'live', 'prague', 'praha', '2026', '2027',
                   '2028', 'europe', 'the', 'and', 'with', 'special', 'guest', 'hoste'}
        return {w for w in t.split() if len(w) >= 4 and w not in ignored}
    aa, bb = important(a), important(b)
    shared = aa & bb
    return bool(shared and (len(shared) >= 2 or any(len(w) >= 7 for w in shared))
                and len(shared) / min(len(aa), len(bb)) >= .65)


def catalogue_title_candidates(anchors, event_url):
    """Read a GoOut card whether the poster and title are separate links.

    In the live catalogue the first <a> pointing at an event is often only a
    cover image. v9.1 placed its URL in 'seen' before checking its text and
    consequently skipped the later, text-bearing <a> with the same URL.

    Collect ALL anchors for an event URL before selecting its title; use
    explicit accessible labels/image alt text and finally its URL slug.
    Extracted catalogue titles are ONLY hints: 'same_event' on the full
    event detail still requires exact date, matching venue and title.
    """
    labels = []
    for a in anchors:
        values = [a.get_text(' ', strip=True), a.get('aria-label', ''),
                  a.get('title', '')]
        for img in a.select('img[alt]'):
            values.append(img.get('alt', ''))
        # A card can be a poster link followed by a heading outside that link.
        # Only inspect nearby heading tags, never the entire page section.
        for parent in list(a.parents)[:3]:
            heading = parent.find(['h2', 'h3', 'h4'], recursive=True)
            if heading is not None:
                values.append(heading.get_text(' ', strip=True))
                break
        for value in values:
            title = ' '.join(str(value or '').split())
            if not 5 <= len(title) <= 150:
                continue
            if norm(title) in {'vstupenky', 'koupit vstupenky', 'tickets',
                               'vyprodano', 'zobrazit vice', 'prodej ukoncen'}:
                continue
            if title not in labels:
                labels.append(title)
    # Some GoOut event cards only contain an <a><img alt=""></a> in the
    # raw server response. The event slug is still a usable SEARCH HINT.
    # It never qualifies as evidence by itself.
    path = urlparse(event_url).path
    m = re.fullmatch(r'/(?:cs|en)/([^/]+)/sz[a-z0-9]+/?', path, re.I)
    if m:
        from urllib.parse import unquote
        slug = unquote(m.group(1)).replace('-', ' ').replace('+', ' ')
        if 5 <= len(slug) <= 150 and slug not in labels:
            labels.append(slug)
    return labels


def extract_goout_catalogue(html, url):
    """Return {event_url: [possible event names]} with image links deduped."""
    soup = BeautifulSoup(html, 'html.parser')
    groups = defaultdict(list)
    for anchor in soup.select('a[href]'):
        event_url = urljoin(url, anchor.get('href', ''))
        if not host_ok(event_url) or not re.fullmatch(
            r'/(?:cs|en)/[^/]+/sz[a-z0-9]+/?', urlparse(event_url).path, re.I
        ):
            continue
        groups[event_url].append(anchor)
    return {event_url: catalogue_title_candidates(anchors, event_url)
            for event_url, anchors in groups.items()}


def discover_goout(events, fetcher, now=None, cache=None):
    """Find candidate URLs; ALWAYS verify actual detail before assigning prices.

    The critical v9 bug: catalogues were discarded between runs. Cache only
    stores *hints*, never prices. Eight new pages are scanned per invocation;
    candidates collected over weeks can thus be reused without re-fetching.
    """
    now = now or datetime.now(timezone.utc)
    cache = cache if cache is not None else {}
    by_city = defaultdict(list)
    for event in events:
        if not NEGATIVE_TITLES.search(str(event.get('title', ''))):
            by_city[city_key(event.get('city'))].append(event)
    stats = {'pages': 0, 'events': 0, 'named': 0}
    for city, sort, page in catalogue_plan(now)[:CATALOG_PAGES_PER_RUN]:
        area = events if city == 'Česko' else by_city.get(city_key(city), [])
        if not area:
            continue
        url = goout_listing_url(city, sort=sort, page=page)
        html, error = fetcher.get_html(url)
        if error:
            print(f'GOOUT KATALOG: {city}, {sort} str.{page}: nedostupný ({error})')
            continue
        entries = extract_goout_catalogue(html, url)
        stats['pages'] += 1
        stats['events'] += len(entries)
        stats['named'] += sum(bool(titles) for titles in entries.values())
        for event_url, names in entries.items():
            if names:
                cache[event_url] = {'names': names[:8], 'city': city,
                                    'last_seen': datetime.now(ZoneInfo('Europe/Prague')).date().isoformat()}
        sample = [names[0][:58] for names in entries.values() if names][:4]
        print(f'GOOUT KATALOG: {city}, {sort} str.{page}: {len(entries)} odkazů, '
              f'{sum(bool(n) for n in entries.values())} se jménem')
        print('  UKÁZKA NÁZVŮ:', ' | '.join(sample) or '(bez použitelného názvu)')
        time.sleep(.2)
    # Cross-run matching against cached candidates. Venue/date are still
    # required in same_event(), so title alone never sets a price.
    links = defaultdict(list)
    for url, record in cache.items():
        names = record.get('names', [])
        area = events if record.get('city') == 'Česko' else by_city.get(city_key(record.get('city')), [])
        for ev in area:
            if any(plausible_identity(ev.get('title'), n) or
                   plausible_identity(ev.get('artist'), n) for n in names):
                if url not in links[ev.get('id')]:
                    links[ev.get('id')].append(url)
    print(f'GOOUT KATALOG CELKEM: {stats["pages"]} nových stran, '
          f'{stats["named"]} názvů, {len(cache)} URL v paměti, '
          f'{sum(map(len, links.values()))} možných shod s UKA (detail je musí potvrdit)')
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
    today = now.astimezone(ZoneInfo('Europe/Prague')).date().isoformat()
    upcoming = [e for e in events if e.get('price') is None and e.get('date', '') >= today
                and not NEGATIVE_TITLES.search(str(e.get('title','')))]
    upcoming.sort(key=lambda e: (e.get('public_price_attempt_at', ''), e.get('date', '9999')))
    report = {'unknown_before': len(upcoming), 'matched': [], 'skipped': defaultdict(int),
              'checked': 0, 'price_sources': defaultdict(int), 'seed_targets': 0}
    details_cache = {}
    cache = load_catalog_cache()
    catalog_urls = discover_goout(upcoming, fetcher, now=now, cache=cache)
    report['catalog_cache'] = cache
    observed_by_id = defaultdict(list)
    for seed in seeds:
        if seed.get('event_id'):
            observed_by_id[seed['event_id']].append(seed)
    report['seed_targets'] = sum(any(seed_matches(ev, x) for x in observed_by_id.get(ev.get('id'), [])) for ev in upcoming)
    for event in upcoming:
        if fetcher.count >= MAX_REQUESTS or time.monotonic() - started > MAX_SECONDS:
            break
        # Check URLs independently. A failed page must never block checking a
        # newly found URL for the same event on a future run.
        attempts = event.get('public_price_attempts', {})
        if not isinstance(attempts, dict):
            attempts = {}
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
        for url in urls[:4]:
            old = attempts.get(url, '')
            try:
                if old and (now.astimezone(ZoneInfo('Europe/Prague')).date() - date.fromisoformat(old)).days < MAX_AGE_DAYS:
                    continue
            except (ValueError, TypeError):
                pass
            seed = next((s for s in seeds if s.get('url') == url and seed_matches(event, s)), None)
            if url not in details_cache:
                details_cache[url] = fetcher.get(url)
                report['checked'] += 1
                time.sleep(.1)
            detail, error = details_cache[url]
            # Track accessible attempted links; temporary blocks retry on next
            # run rather than suppressing this event for seven days.
            if error not in {'robots/unavailable', 'redirect disallowed', 'ConnectionError', 'Timeout', 'HTTP 429', 'HTTP 403'}:
                attempts[url] = today
                event['public_price_attempts'] = dict(list(attempts.items())[-30:])
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
    report['cached_candidates'] = len(cache)
    report['ignored_addons'] = sum(1 for e in events if e.get('price') is None and NEGATIVE_TITLES.search(str(e.get('title',''))))
    return report


def run(dry_run=False):
    data = json.loads(EVENTS_FILE.read_text('utf-8'))
    events = data.get('events')
    if not isinstance(events, list): raise RuntimeError('events.json: očekávám {"events":[...]}')
    before = json.dumps(events, sort_keys=True, ensure_ascii=False)
    report = process(events, RespectfulFetcher(), load_seeds())
    print(f'VEŘEJNÉ CENY: {report["checked"]} detailů, {len(report["matched"])} nových cen, '
          f'{report["unknown_after"]} stále neznámých; {report["requests"]} HTML požadavků, '
          f'{report["index_matches"]} možných shod v katalozích; uložený index {len(report["catalog_cache"])}; přeskočené doplňky {report["ignored_addons"]}')
    print(f'SHODA S ODKAZY: {report["seed_targets"]} akcí s chybějící cenou z aktuální databáze')
    for key, num in report['price_sources'].items(): print(f'  ZDROJ: {key}: {num}')
    for key, num in report['skipped'].items(): print(f'  Přeskočeno – {key}: {num}')
    for m in report['matched']:
        print('  NALEZENO:', m['title'], '=>', m['price'], 'Kč;', m['type'], '; zdroj:', m['url'])
    if dry_run:
        print('TESTOVACÍ REŽIM: events.json zůstává beze změny.')
        return report
    persist_catalog_cache(report['catalog_cache'])
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
