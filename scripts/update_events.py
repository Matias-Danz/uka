#!/usr/bin/env python3
"""UKA public events updater.

O2 and O2 universum official listings + Ticketmaster Discovery API.
Prices come from O2 official detail pages, Ticketmaster event API details,
and optionally Ticketmaster public event pages only when allowed by robots.txt.
Unknown prices stay unknown. No bypass of technical access controls.
"""
from __future__ import annotations

import argparse
import copy
from difflib import SequenceMatcher
import json
import os
import math
import re
import sys
import time
import unicodedata
from datetime import datetime, date, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parents[1]
EVENT_FILE = ROOT / "events.json"
SOURCES = (
    {
        "name": "O2 arena – oficiální program",
        "url": "https://www.o2arena.cz/filter/concerts/",
        "host": "www.o2arena.cz",
        "venue": "O2 arena",
        "city": "Praha",
        "address": "Českomoravská 2345/17a, Praha 9",
        "lat": 50.10475,
        "lng": 14.49362,
        "id_prefix": "o2-auto",
    },
    {
        "name": "O2 universum – oficiální program",
        "url": "https://www.o2universum.cz/filter/concerts/",
        "host": "www.o2universum.cz",
        "venue": "O2 universum",
        "city": "Praha",
        "address": "Českomoravská 2345/17, Praha 9",
        # Souřadnice O2 universum (orientační střed budovy).
        "lat": 50.10366,
        "lng": 14.49330,
        "id_prefix": "o2-universum-auto",
    },
)
UA = "UKA-MusicEvents/0.4 (public event metadata only; respects robots.txt)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept-Language": "cs-CZ,cs;q=0.9"})
DATE_RX = re.compile(r"(?<!\d)(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d{2})(?:\s*(\d{1,2}):(\d{2}))?")
# Max. 18 individual event pages per run; missing prices finish over successive hourly runs.
MAX_DETAIL_PAGES_PER_RUN = 18
# Prices automatically sourced by this script are rechecked every 7 days.
PRICE_RECHECK_DAYS = 7



def now_cz():
    return datetime.now(ZoneInfo("Europe/Prague"))


def canonical_url(url: str) -> str:
    p = urlparse(url)
    return urlunparse((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/") + "/", "", "", ""))


def get_robots(url: str) -> RobotFileParser | None:
    origin = urlparse(url)
    robots_url = f"{origin.scheme}://{origin.netloc}/robots.txt"
    try:
        resp = SESSION.get(robots_url, timeout=16)
        if resp.status_code != 200:
            print(f"SKIP: robots.txt returned {resp.status_code} for {origin.netloc}", file=sys.stderr)
            return None
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.parse(resp.text.splitlines())
        if not rp.can_fetch(UA, url):
            print(f"SKIP: robots.txt disallows {url}", file=sys.stderr)
            return None
        return rp
    except requests.RequestException as exc:
        print(f"SKIP: cannot check robots.txt: {exc}", file=sys.stderr)
        return None


def fetch(url: str, robot: RobotFileParser) -> str | None:
    if not robot.can_fetch(UA, url):
        print(f"SKIP: disallowed URL {url}")
        return None
    try:
        resp = SESSION.get(url, timeout=22)
        resp.raise_for_status()
        if len(resp.content) > 3_000_000:
            raise ValueError("Page unexpectedly large")
        return resp.text
    except (requests.RequestException, ValueError) as exc:
        print(f"Fetch failed: {url}: {exc}", file=sys.stderr)
        return None


def parse_event_dates(heading: Tag) -> list[tuple[str, str]]:
    """Read one or more event dates immediately preceding a program h3.

    Works for e.g. `10.11.2026 20:00`, `11.11.2026 20:00` before Kabát.
    Does not guess when a date cannot be found in the listing.
    """
    matches = []
    seen = set()
    node = heading.previous_element
    checked = 0
    while node is not None and checked < 120:
        checked += 1
        if isinstance(node, Tag) and node.name == "h3":
            break
        if isinstance(node, NavigableString):
            for mat in DATE_RX.finditer(str(node)):
                day, month, year, hour, minute = mat.groups()
                try:
                    dt = date(int(year), int(month), int(day)).isoformat()
                except ValueError:
                    continue
                tm = f"{int(hour):02}:{minute}" if hour is not None else ""
                key = dt, tm
                if key not in seen:
                    seen.add(key)
                    matches.append(key)
        node = node.previous_element
    return list(reversed(matches))[:5]


# Odstraňuje jasně nehudební události z občas smíšeného programu haly.
NON_MUSIC_RX = re.compile(
    r"(?:\bhc\s+sparta\b|\bhokej\b|\bprohl[ií]dkov[eé]\s+okruhy\b|"
    r"\bzr[aá]dci:\s+posledn[ií]\s+st[uů]l\b|\bexkurze\b)",
    flags=re.IGNORECASE,
)


def extract_program(html_text: str, spec: dict) -> list[dict]:
    doc = BeautifulSoup(html_text, "html.parser")
    candidates: list[dict] = []
    seen = set()
    for heading in doc.find_all("h3"):
        link = heading.find("a", href=True) or heading.find_parent("a", href=True)
        if not link:
            continue
        url = canonical_url(urljoin(spec["url"], link["href"]))
        parsed = urlparse(url)
        if parsed.netloc != spec["host"] or not parsed.path.startswith("/events/"):
            continue
        title = heading.get_text(" ", strip=True)
        if not title or len(title) > 160 or NON_MUSIC_RX.search(title):
            continue
        for dt, tm in parse_event_dates(heading):
            key = url, dt
            if key in seen:
                continue
            seen.add(key)
            candidates.append({"title": title, "date": dt, "time": tm, "url": url})
    return candidates


def event_image(detail_html: str, event_url: str) -> str:
    soup = BeautifulSoup(detail_html, "html.parser")
    for attrs in ({"property": "og:image"}, {"name": "twitter:image"}):
        node = soup.find("meta", attrs=attrs)
        if node and node.get("content"):
            resolved = urljoin(event_url, node["content"])
            if urlparse(resolved).scheme == "https":
                return resolved
    return ""


def parse_price_value(value: str) -> tuple[int, int | None] | None:
    """Parse only an explicit Czech entry price, not any unrelated amount in the description.

    Examples: '1 190 – 4 390 Kč', 'od 750 Kč', '790 Kč', 'Zdarma'.
    Returns (minimum, maximum), with maximum=None for single 'from' prices.
    """
    clean = re.sub(r"\s+", " ", value.replace("\xa0", " ").replace("\u202f", " ")).strip(" :|\t")
    if clean.casefold() in {"zdarma", "vstup zdarma", "vstupné zdarma", "0 kč"}:
        return 0, 0
    # Intentionally anchored to the whole price field, so VIP offers and prices
    # mentioned in the body of an event cannot accidentally be read as entrance.
    match = re.fullmatch(
        r"(?:od\s+)?(?P<low>\d[\d ]*)\s*(?:(?:–|—|-|až)\s*(?P<high>\d[\d ]*))?\s*(?:Kč|CZK)",
        clean, flags=re.IGNORECASE,
    )
    if not match:
        return None
    low = int(match.group("low").replace(" ", ""))
    high = int(match.group("high").replace(" ", "")) if match.group("high") else None
    if low < 0 or low > 200_000 or (high is not None and (high < low or high > 200_000)):
        return None
    return low, high


def event_price(detail_html: str) -> tuple[int, int | None] | None:
    """Take 'Cena' from the official event's info table, NOT all prices on the page.

    O2 arena displays the public price range right under the explicit label 'Cena'.
    Ignore special wheelchair / VIP pricing lower in the page.
    """
    soup = BeautifulSoup(detail_html, "html.parser")
    strings = [re.sub(r"\s+", " ", x).strip() for x in soup.stripped_strings]
    for idx, entry in enumerate(strings):
        # Label and price can be within one text node.
        inline = re.fullmatch(r"Cena\s*[:|]\s*(.+)", entry, flags=re.IGNORECASE)
        if inline:
            found = parse_price_value(inline.group(1))
            if found is not None:
                return found
        if not re.fullmatch(r"Cena\s*:?(?:\s*\|)?", entry, flags=re.IGNORECASE):
            continue
        # The label and amounts can be split over several markup nodes.
        following = [x for x in strings[idx+1:idx+5] if x not in {"|", ":"}]
        for length in range(1, min(4, len(following)) + 1):
            found = parse_price_value(" ".join(following[:length]))
            if found is not None:
                return found
    return None


def needs_price_check(event: dict, today: str) -> bool:
    last = event.get("price_checked_at")
    if not isinstance(last, str):
        return True
    try:
        age = (date.fromisoformat(today) - date.fromisoformat(last[:10])).days
    except ValueError:
        return True
    # Recheck missing price every 3 days, known prices once every 7 days.
    limit = 3 if event.get("price") is None else PRICE_RECHECK_DAYS
    return age >= limit


def allowed_official_detail(url: str, spec: dict) -> bool:
    parsed = urlparse(url)
    return (parsed.scheme == "https" and parsed.netloc == spec["host"]
            and parsed.path.startswith("/events/"))


def normalize_title(title: str) -> str:
    """Use one stable normalized title to avoid an existing same-day venue duplicate."""
    value = unicodedata.normalize("NFKD", title).casefold()
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", value)


def update_from_sources(events: list[dict], today: str) -> tuple[list[dict], int]:
    found = 0
    for spec in SOURCES:
        # Index vždy jen v rámci konkrétní haly, aby se události nespojily napříč místy.
        by_url_date = {
            (canonical_url(e.get("ticket_url", "")), e.get("date")): e
            for e in events if e.get("ticket_url") and e.get("venue") == spec["venue"]
        }
        by_title_date = {
            (normalize_title(e.get("title", "")), e.get("date")): e
            for e in events if e.get("venue") == spec["venue"]
        }
        robot = get_robots(spec["url"])
        if robot is None:
            continue

        page_cache: dict[str, str | None] = {}
        requests_used = 0

        def detail(url: str) -> str | None:
            nonlocal requests_used
            url = canonical_url(url)
            if url in page_cache:
                return page_cache[url]
            if not allowed_official_detail(url, spec) or requests_used >= MAX_DETAIL_PAGES_PER_RUN:
                return None
            requests_used += 1
            result = fetch(url, robot)
            page_cache[url] = result
            time.sleep(0.8)  # gentle rate limit, no request to ticket vendors
            return result

        def enrich(event: dict, detail_html: str, detail_url: str) -> None:
            if not event.get("image_url"):
                image = event_image(detail_html, detail_url)
                if image:
                    event["image_url"] = image
                    event["image_credit"] = spec["venue"] + " / pořadatel"
            # Never overwrite an independently-entered price. Periodically refresh
            # only prices recorded by the automated O2 price extractor.
            if event.get("price") is None or event.get("price_source") == spec["venue"]:
                price = event_price(detail_html)
                event["price_checked_at"] = today
                if price is not None:
                    event["price"], event["price_max"] = price
                    event["price_source"] = spec["venue"]
                    print(f"PRICE: {event.get('title', '')}: {price[0]} - {price[1]} CZK")
                else:
                    print(f"PRICE UNKNOWN: {event.get('title', '')}")

        listing_html = fetch(spec["url"], robot)
        candidates = extract_program(listing_html, spec) if listing_html else []
        print(f"{spec['name']}: {len(candidates)} dated events in listing")
        if not candidates:
            print("WARNING: no event candidates in listing; keeping previous data", file=sys.stderr)

        for c in candidates:
            if c["date"] < today:
                continue
            existing = (by_url_date.get((c["url"], c["date"]))
                        or by_title_date.get((normalize_title(c["title"]), c["date"])))
            if existing is not None:
                official = allowed_official_detail(existing.get("ticket_url", ""), spec)
                # Prefer the official URL from the programme even if the original
                # old event links to an external ticket seller.
                if ((existing.get("price") is None or existing.get("price_source") == spec["venue"])
                        and needs_price_check(existing, today)) or not existing.get("image_url"):
                    html = detail(c["url"])
                    if html:
                        enrich(existing, html, c["url"])
                continue

            slug = urlparse(c["url"]).path.strip("/").split("/")[-1]
            event = {
                "id": f"{spec['id_prefix']}-{slug}-{c['date']}",
                "title": c["title"], "artist": c["title"], "category": "koncert",
                "venue": spec["venue"], "city": spec["city"],
                "address": spec["address"], "lat": spec["lat"], "lng": spec["lng"],
                "date": c["date"], "time": c["time"],
                "price": None, "price_max": None,
                "ticket_url": c["url"], "source": spec["name"], "verified_at": today,
                "description": "Akce z programu " + spec["venue"] + ". Aktuální ceny ověřuj u pořadatele.",
                "image_url": "", "image_credit": "",
            }
            html = detail(c["url"])
            if html:
                enrich(event, html, c["url"])
            events.append(event)
            by_url_date[(c["url"], c["date"])] = event
            by_title_date[(normalize_title(c["title"]), c["date"])] = event
            found += 1

        # Also process older O2 records that aren't currently in the listing,
        # but already contain the official event-detail URL.
        for event in events:
            if requests_used >= MAX_DETAIL_PAGES_PER_RUN:
                break
            if (event.get("venue") != spec["venue"] or not needs_price_check(event, today)
                    or (event.get("price") is not None and event.get("price_source") != spec["venue"])):
                continue
            url = event.get("ticket_url", "")
            if not allowed_official_detail(url, spec):
                continue
            html = detail(url)
            if html:
                enrich(event, html, url)

        print(f"{spec['name']}: {found} new events; {requests_used} detail pages checked")
    return events, found


# Ticketmaster: dokumentované Discovery API (pouze se soukromým klíčem z GitHub Secrets).
TICKETMASTER_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
TM_MAX_PAGES_PER_CLASS = 8  # omezení dotazů i počtu stránek v jedné aktualizaci
TM_MAX_PRICE_CHECKS_PER_RUN = 24  # postupné doplňování cen starších koncertů
TM_PRICE_RETRY_DAYS = 3  # chybějící cenu zkusíme znovu až za 3 dny
TM_PRICE_REFRESH_DAYS = 7  # ceny získané automaticky po týdnu ověříme
TM_DETAIL_URL = "https://app.ticketmaster.com/discovery/v2/events/{event_id}.json"
TM_ALLOWED_PAGE_HOSTS = frozenset({"www.ticketmaster.cz", "ticketmaster.cz"})


def tm_category(item: dict) -> str:
    if item.get("_uka_classification") == "opera":
        return "opera"
    classes = item.get("classifications") or []
    genres = " ".join(
        str(c.get("genre", {}).get("name", "")) + " "
        + str(c.get("subGenre", {}).get("name", ""))
        for c in classes if isinstance(c, dict)
    ).casefold()
    title = str(item.get("name", "")).casefold()
    if "festival" in title or "festival" in genres:
        return "festival"
    if any(x in genres for x in ("electronic", "dance", "techno", "trance", "house", "edm")):
        return "rave"
    return "koncert"


def tm_price(item: dict) -> tuple[int | None, int | None]:
    """Nepřevádět USD/EUR na Kč; není-li CZK, cena zůstane neznámá."""
    prices = []
    for row in item.get("priceRanges") or []:
        if not isinstance(row, dict) or row.get("currency", "").upper() != "CZK":
            continue
        if row.get("type", "standard").casefold() not in ("standard", ""):
            continue
        try:
            low = float(row["min"])
            high = float(row.get("max", low))
        except (KeyError, ValueError, TypeError):
            continue
        if all(map(math.isfinite, (low, high))) and 0 <= low <= high <= 200_000:
            prices.append((low, high))
    if not prices:
        return None, None
    return round(min(low for low, _ in prices)), round(max(high for _, high in prices))


def tm_page_price(html: str) -> tuple[int | None, int | None]:
    """Conservatively parse ticket-per-piece CZK prices from public event HTML.

    Do NOT parse arbitrary sums in event descriptions or cart totals.
    Page prices are indicative, availability should be checked on the seller site.
    """
    soup = BeautifulSoup(html, "html.parser")
    # Public JSON-LD Event offers are useful if the ticket list is rendered by JS.
    # Only take prices explicitly belonging to an Event, not unrelated page offers.
    structured: list[tuple[float, float]] = []

    def to_number(value):
        if isinstance(value, (int, float)):
            return float(value)
        if not isinstance(value, str):
            raise ValueError("Not numeric")
        normalized = value.strip().replace("\xa0", " ").replace("\u202f", " ")
        normalized = normalized.replace(" ", "")
        if "," in normalized:
            normalized = normalized.replace(".", "").replace(",", ".")
        return float(normalized)

    def walk_json(value):
        if isinstance(value, list):
            for child in value:
                walk_json(child)
        elif isinstance(value, dict):
            typ = value.get("@type", "")
            typelist = typ if isinstance(typ, list) else [typ]
            if any(isinstance(t, str) and t.lower().endswith("event") for t in typelist):
                offers = value.get("offers") or []
                if isinstance(offers, dict):
                    offers = [offers]
                for offer in offers if isinstance(offers, list) else []:
                    if not isinstance(offer, dict) or str(offer.get("priceCurrency", "")).upper() != "CZK":
                        continue
                    try:
                        lo = to_number(offer.get("lowPrice", offer.get("price")))
                        hi = to_number(offer.get("highPrice", offer.get("price", lo)))
                        if all(map(math.isfinite, (lo, hi))) and 0 <= lo <= hi <= 200_000:
                            structured.append((lo, hi))
                    except (ValueError, TypeError, OverflowError):
                        continue
            if "@graph" in value:
                walk_json(value["@graph"])

    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            walk_json(json.loads(tag.string or tag.get_text()))
        except (ValueError, TypeError):
            pass

    for tag in soup(["script", "style", "template", "noscript"]):
        tag.decompose()
    plain = soup.get_text(" ", strip=True).replace("\xa0", " ").replace("\u202f", " ")
    plain = re.sub(r"\s+", " ", plain)
    amount = r"(?:\d{1,3}(?:[ ,. ]\d{3})+|\d{1,6})(?:[,\.]\d{2})?"
    pattern = re.compile(
        rf"(?<!\d)({amount})\s*(?:Kč|CZK)"
        rf"(?:\s*[–—-]\s*({amount})\s*(?:Kč|CZK))?"
        r"\s*(?:za kus|per ticket|each)\b", re.IGNORECASE)

    def number(s: str) -> float:
        clean = s.replace(" ", "")
        if "," in clean and "." in clean:
            # 1,190.00 (EN) versus 1.190,00 (CS).
            clean = (clean.replace(",", "") if clean.rfind(".") > clean.rfind(",")
                     else clean.replace(".", "").replace(",", "."))
        elif "," in clean:
            clean = clean.replace(",", "") if re.search(r",\d{3}$", clean) else clean.replace(",", ".")
        elif "." in clean and re.search(r"\.\d{3}$", clean):
            clean = clean.replace(".", "")
        return float(clean)

    found: list[tuple[float, float]] = []
    for m in pattern.finditer(plain):
        try:
            low = number(m.group(1))
            high = number(m.group(2)) if m.group(2) else low
        except ValueError:
            continue
        if all(map(math.isfinite, (low, high))) and 0 <= low <= high <= 200_000:
            found.append((low, high))
    # Prefer visible ticket prices when present; fall back to schema.org Offers.
    found = found or structured
    if not found:
        return None, None
    return round(min(a for a, _ in found)), round(max(b for _, b in found))


def tm_price_check_due(e: dict, today: str) -> bool:
    """Only touch missing prices or previously machine-sourced Ticketmaster prices."""
    current = e.get("price")
    if current is not None and e.get("price_source") not in ("Ticketmaster", "Ticketmaster (stránka)"):
        return False
    try:
        last = date.fromisoformat(str(e.get("tm_price_checked_at", ""))[:10])
        interval = TM_PRICE_RETRY_DAYS if current is None else TM_PRICE_REFRESH_DAYS
        return (date.fromisoformat(today) - last).days >= interval
    except (ValueError, TypeError):
        return True


def tm_detail_price(event_id: str, api_key: str) -> tuple[int | None, int | None]:
    """Official Discovery event detail sometimes has priceRanges absent from search."""
    # IDs from existing event records, not user-input URLs.
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,80}", event_id):
        return None, None
    try:
        r = SESSION.get(TM_DETAIL_URL.format(event_id=event_id),
                        params={"apikey": api_key}, timeout=16)
        if r.status_code == 200:
            return tm_price(r.json())
        print(f"TM detail price HTTP {r.status_code} (event ID not logged)")
    except (requests.RequestException, ValueError, TypeError) as exc:
        print(f"TM detail price unavailable: {type(exc).__name__}")
    return None, None


def tm_web_price(event_url: str, robots_cache: dict) -> tuple[int | None, int | None]:
    """Optional public ticket page fallback, strictly robots-guarded and rate-limited.

    No scripted checkout, dynamic APIs, CAPTCHA, cookie or bot-block bypass.
    """
    parsed = urlparse(event_url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in TM_ALLOWED_PAGE_HOSTS or not parsed.path.startswith("/event/"):
        return None, None
    if not parsed.path.startswith("/event/") or len(event_url) > 1000:
        return None, None
    origin = f"{parsed.scheme}://{parsed.netloc.lower()}"
    if origin not in robots_cache:
        robots_cache[origin] = get_robots(event_url)
    rp = robots_cache[origin]
    if rp is None or not rp.can_fetch(UA, event_url):
        return None, None
    try:
        response = SESSION.get(event_url, timeout=18, allow_redirects=False)
        if response.status_code != 200 or len(response.content) > 3_000_000:
            print(f"TM public price page unavailable (HTTP {response.status_code})")
            return None, None
        return tm_page_price(response.text)
    except requests.RequestException as exc:
        print(f"TM public page fetch failed: {type(exc).__name__}")
        return None, None


def tm_enrich_prices(events: list[dict], today: str, api_key: str) -> None:
    """Backfill already-imported events, no duplicates or overwrites of manual prices."""
    candidates = [e for e in events
                  if (str(e.get("id", "")).startswith("ticketmaster-")
                      and e.get("date", "") >= today
                      and tm_price_check_due(e, today))]
    # Give priority to unknown prices and closest concerts.
    candidates.sort(key=lambda e: (e.get("price") is not None, e.get("date", "9999")))
    checked = filled = 0
    robots_cache: dict = {}
    for e in candidates[:TM_MAX_PRICE_CHECKS_PER_RUN]:
        eid = str(e["id"])[len("ticketmaster-"):]
        low, high = tm_detail_price(eid, api_key)
        method = "Ticketmaster"
        if low is None:
            # Some public pages expose actual per-ticket prices absent from API.
            # Only read if the site explicitly permits robots access.
            low, high = tm_web_price(str(e.get("ticket_url") or ""), robots_cache)
            method = "Ticketmaster (stránka)"
        e["tm_price_checked_at"] = today
        checked += 1
        if low is not None:
            if e.get("price") is None or e.get("price_source") in ("Ticketmaster", "Ticketmaster (stránka)"):
                was_missing = e.get("price") is None
                e["price"], e["price_max"], e["price_source"] = low, high, method
                if was_missing:
                    filled += 1
        time.sleep(0.25)
    missing_total = sum(1 for e in events if str(e.get("id", "")).startswith("ticketmaster-") and e.get("price") is None)
    print(f"TM prices: {checked} checked this run, {filled} newly filled, {missing_total} still unknown")


def tm_image(item: dict) -> str:
    options = [x for x in item.get("images", []) if isinstance(x, dict)
               and x.get("url", "").startswith("https://") and not x.get("fallback")]
    if not options:
        return ""
    # Prefer relevant landscape image, not thumbnail or 5 MB hero.
    options.sort(key=lambda x: (x.get("ratio") != "16_9",
                                abs(int(x.get("width") or 0) - 1000)))
    return options[0]["url"]


def normalize_venue(name: str) -> str:
    name = normalize_title(name or "")
    return {"o2arena": "o2arena", "o2universum": "o2universum"}.get(name, name)


def likely_same_show(a: dict, b: dict) -> bool:
    if a.get("date") != b.get("date") or normalize_venue(a.get("venue", "")) != normalize_venue(b.get("venue", "")):
        return False
    left, right = normalize_title(a.get("title", "")), normalize_title(b.get("title", ""))
    if not left or not right:
        return False
    if left == right:
        return True
    # Názvy se často mírně liší (přidaný název turné nebo speciální host).
    if min(len(left), len(right)) >= 12 and (left in right or right in left):
        return True
    return min(len(left), len(right)) >= 8 and SequenceMatcher(None, left, right).ratio() >= 0.90


def tm_convert(item: dict, today: str) -> dict | None:
    """Map music event to existing UKA schema; reject unsupported/no-location entries."""
    try:
        eid = str(item["id"])
        title = str(item["name"]).strip()
        event_date = item["dates"]["start"]["localDate"]
        date.fromisoformat(event_date)
        if not eid or not title or event_date < today:
            return None
        if (item.get("dates", {}).get("status") or {}).get("code", "").casefold() in ("cancelled", "canceled", "rescheduled"):
            return None
        venue = (item.get("_embedded", {}).get("venues") or [])[0]
        if (venue.get("country") or {}).get("countryCode") != "CZ":
            return None
        pos = venue["location"]
        lat, lng = float(pos["latitude"]), float(pos["longitude"])
        if not (48.4 <= lat <= 51.2 and 12 <= lng <= 19 and math.isfinite(lat) and math.isfinite(lng)):
            return None
        vname = str(venue.get("name") or "").strip()
        city = str((venue.get("city") or {}).get("name") or "").strip()
        if not vname or not city:
            return None
        link = str(item.get("url") or "")
        if not link.startswith("https://"):
            return None
        address = (venue.get("address") or {}).get("line1") or ""
        price, price_max = tm_price(item)
        artist_items = item.get("_embedded", {}).get("attractions") or []
        artists = ", ".join(str(a.get("name", "")).strip() for a in artist_items[:4] if a.get("name"))
        return {
            "id": "ticketmaster-" + eid,
            "title": title,
            "artist": artists or title,
            "category": tm_category(item),
            "venue": vname,
            "city": city,
            "address": address,
            "lat": lat, "lng": lng,
            "date": event_date,
            "time": item.get("dates", {}).get("start", {}).get("localTime", "")[:5],
            "price": price, "price_max": price_max,
            "price_source": "Ticketmaster" if price is not None else "",
            "ticket_url": link,
            "source": "Ticketmaster Discovery API",
            "verified_at": today,
            "description": "Informace poskytuje Ticketmaster. Vstupenky a případné změny ověř u prodejce.",
            "image_url": tm_image(item),
            "image_credit": "Ticketmaster / pořadatel" if tm_image(item) else "",
        }
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
        return None


def update_ticketmaster(events: list[dict], today: str) -> tuple[list[dict], int]:
    key = os.environ.get("TICKETMASTER_API_KEY", "").strip()
    if not key:
        print("SKIP Ticketmaster: není nastaven TICKETMASTER_API_KEY v GitHub Secrets")
        return events, 0
    existing_by_id = {e.get("id"): e for e in events}
    existing_by_show = {
        (e.get("date"), normalize_venue(e.get("venue", "")), normalize_title(e.get("title", ""))): e
        for e in events if e.get("title") and e.get("venue")
    }
    count = enriched = 0
    for classification in ("music", "opera"):
        for page in range(TM_MAX_PAGES_PER_CLASS):
            # Key never logged or printed. Only backend GitHub Action uses this key.
            params = {
                "apikey": key, "countryCode": "CZ", "classificationName": classification,
                "startDateTime": today + "T00:00:00Z", "size": 100, "page": page,
                "sort": "date,asc", "includeTBA": "no", "includeTBD": "no",
            }
            try:
                res = SESSION.get(TICKETMASTER_URL, params=params, timeout=25)
                if res.status_code != 200:
                    print(f"WARNING Ticketmaster API: HTTP {res.status_code} ({classification}), data kept", file=sys.stderr)
                    break
                payload = res.json()
            except (requests.RequestException, ValueError) as ex:
                # Do not leak API Key via exception URL.
                print(f"WARNING Ticketmaster API: {type(ex).__name__}; data kept", file=sys.stderr)
                break
            raw = payload.get("_embedded", {}).get("events", [])
            for item in raw:
                if not isinstance(item, dict):
                    continue
                item["_uka_classification"] = classification
                candidate = tm_convert(item, today)
                if candidate is None:
                    continue
                match_key = (candidate["date"], normalize_venue(candidate["venue"]),
                             normalize_title(candidate["title"]))
                previous = existing_by_id.get(candidate["id"]) or existing_by_show.get(match_key)
                if previous is None:
                    previous = next((e for e in events if likely_same_show(e, candidate)), None)
                if previous is not None:
                    # Never overwrite hand-edited prices and images; fill missing fields.
                    if previous.get("price") is None and candidate["price"] is not None:
                        previous["price"] = candidate["price"]
                        previous["price_max"] = candidate["price_max"]
                        previous["price_source"] = "Ticketmaster"
                        enriched += 1
                    elif (candidate["price"] is not None
                          and previous.get("price_source") == "Ticketmaster"):
                        # Never replace a known price with a missing API price.
                        previous["price"] = candidate["price"]
                        previous["price_max"] = candidate["price_max"]
                    if not previous.get("image_url") and candidate.get("image_url"):
                        previous["image_url"] = candidate["image_url"]
                        previous["image_credit"] = candidate["image_credit"]
                    continue
                events.append(candidate)
                existing_by_id[candidate["id"]] = candidate
                existing_by_show[match_key] = candidate
                count += 1
            total = payload.get("page", {}).get("totalPages", 1)
            print(f"Ticketmaster {classification}: page {page+1}/{total}, received {len(raw)}")
            if not raw or page + 1 >= total:
                break
            time.sleep(0.4)
    # Try both Discovery detail data and permitted public price pages for missing
    # prices, including records created by previous versions of the importer.
    tm_enrich_prices(events, today, key)
    print(f"Ticketmaster: {count} new events, {enriched} existing prices filled by listings")
    return events, count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline-cleanup", action="store_true", help="Prune past events without accessing the network")
    args = parser.parse_args()
    now = now_cz()
    today = now.date().isoformat()
    data = json.loads(EVENT_FILE.read_text(encoding="utf-8"))
    old_events = data.get("events", [])
    if not isinstance(old_events, list):
        raise RuntimeError("Invalid events.json")
    # Remove past events and obvious non-music entries previously inserted by O2 auto importer.
    events = [copy.deepcopy(e) for e in old_events
              if isinstance(e, dict) and e.get("date", "") >= today
              and not (str(e.get("id", "")).startswith("o2-auto-")
                       and NON_MUSIC_RX.search(str(e.get("title", ""))))]
    past_count = len(old_events) - len(events)
    new_count = 0
    if not args.offline_cleanup:
        events, new_count = update_from_sources(events, today)
        events, new_tm = update_ticketmaster(events, today)
        new_count += new_tm
    events.sort(key=lambda e: (e["date"], e.get("title", "")))
    unique = {}
    for event in events:
        unique[event["id"]] = event
    events = sorted(unique.values(), key=lambda e: (e["date"], e.get("title", "")))
    if events != old_events:
        data["events"] = events
        data["updated_at"] = now.isoformat(timespec="seconds")
        EVENT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"UPDATED: {new_count} newly announced, {past_count} past, {len(events)} total")
    else:
        print(f"NO CHANGES: {len(events)} upcoming events")
    return 0


if __name__ == "__main__":
    sys.exit(main())
