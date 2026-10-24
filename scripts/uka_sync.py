#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UKA unified hourly sync. Original source sections are scoped for safety.

1) Official O2 + Ticketmaster event listing
2) Phase/price enrichment from authorized, accessible sources
3) GoOut public-price discovery (dry-run by default)

All persistent data, overrides and cache live in ../events.json.
This file intentionally preserves the proven source logic with section markers,
while removing dependencies on the old auxiliary files.
"""
from __future__ import annotations
import argparse
import sys


# ========================================================================
# EVENTS: O2 + TICKETMASTER
# ========================================================================
def _build_importer():
    #!/usr/bin/env python3
    """UKA public events updater.

    O2 and O2 universum official listings + Ticketmaster Discovery API.
    Prices come from O2 official detail pages, Ticketmaster event API details,
    and optionally Ticketmaster public event pages only when allowed by robots.txt.
    Unknown prices stay unknown. No bypass of technical access controls.
    """

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
    TM_MAX_PRICE_CHECKS_PER_RUN = 35  # postupně doplňovat chybějící ceny, bez přetížení prodejce
    TM_PRICE_RETRY_DAYS = 2  # chybějící cenu zkusíme znovu za 2 dny
    TM_PRICE_REFRESH_DAYS = 7  # ceny získané automaticky po týdnu ověříme
    TM_DETAIL_URL = "https://app.ticketmaster.com/discovery/v2/events/{event_id}.json"
    TM_ALLOWED_PAGE_HOSTS = frozenset({"www.ticketmaster.cz", "ticketmaster.cz"})


    def tm_sale_phase(item: dict, at=None) -> str | None:
        """Official *sales window*, not verified inventory. Called from Discovery listings.

        Never infer that 'Buy tickets' / 'onsale' guarantees remaining seats.
        """
        now = at or now_cz()
        code = str((item.get('dates', {}).get('status') or {}).get('code', '')).casefold()
        if code in ('canceled', 'cancelled', 'postponed', 'rescheduled'):
            return 'paused'
        public = (item.get('sales') or {}).get('public') or {}
        def at_time(value):
            try:
                dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
                return dt if dt.tzinfo else None
            except (ValueError, TypeError):
                return None
        begins = at_time(public.get('startDateTime'))
        ends = at_time(public.get('endDateTime'))
        if begins and now < begins:
            return 'upcoming'
        if ends and now >= ends:
            return 'closed'
        if code == 'onsale' and (not begins or begins <= now) and (not ends or now < ends):
            return 'on_sale'
        return None

    def tm_set_sale_phase(event: dict, item: dict, at=None) -> None:
        """Refresh sales phase once per 18h, or immediately when the phase changes."""
        now = at or now_cz()
        phase = tm_sale_phase(item, now)
        if not phase:
            return
        last = event.get('sales_phase_checked_at')
        age_hours = 10_000
        if isinstance(last, str):
            try:
                checked = datetime.fromisoformat(last.replace('Z', '+00:00'))
                if checked.tzinfo:
                    age_hours = (now-checked).total_seconds()/3600
            except ValueError:
                pass
        if event.get('sales_phase') != phase or age_hours >= 18:
            event['sales_phase'] = phase
            event['sales_phase_checked_at'] = now.isoformat(timespec='seconds')
            event['sales_phase_source'] = 'Ticketmaster Discovery API'

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
            if all(map(math.isfinite, (low, high))) and 0 < low <= high <= 200_000:
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
                            if all(map(math.isfinite, (lo, hi))) and 0 < lo <= hi <= 200_000:
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
            r"\s*(?:za\s+kus|za\s+vstupenku|per\s+ticket|each|/\s*ks|/\s*ticket)\b", re.IGNORECASE)

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

        # Ticketmaster often renders ticket categories as "Plocha 890,00 Kč za kus".
        # Restrict extraction to the current event's purchase region, *before* the
        # cart/FAQ/related-events footer. Related concerts must never supply a price.
        start_candidates = [plain.find(x) for x in ('Všechny ceny', 'All prices', 'Vyberte vstupenky', 'Select Tickets') if plain.find(x) >= 0]
        stop_candidates = [plain.find(x) for x in ('Vstupenek v košíku:', 'Tickets in your cart:', 'Limit vstupenek na akci:',
                                                 'Otevřít detailní informace o místě', 'Informace o místě konání',
                                                 'Zahájení prodeje vstupenek', '## Často kladené otázky') if plain.find(x) >= 0]
        start = min(start_candidates) if start_candidates else 0
        stop = min([pos for pos in stop_candidates if pos > start], default=len(plain))
        section = plain[start:stop]
        # Keep scope narrow when the public detail has no purchase widget yet.
        # Unscoped source text can contain ticket prices for entirely other events.
        if not start_candidates:
            section = plain[:min(stop, 15000)]
        found: list[tuple[float, float]] = []
        for m in pattern.finditer(section):
            try:
                low = number(m.group(1))
                high = number(m.group(2)) if m.group(2) else low
            except ValueError:
                continue
            if all(map(math.isfinite, (low, high))) and 0 < low <= high <= 200_000:
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


    def tm_web_price(event_url: str, robots_cache: dict, stats: dict) -> tuple[int | None, int | None]:
        """Read public visible per-ticket CZK price data when this is permitted.

        Browsing the event page is not a replacement for access to restricted
        seat inventory or a logged-in checkout. Never bypass anti-bot controls.
        """
        parsed = urlparse(event_url)
        if (parsed.scheme != "https" or parsed.netloc.lower() not in TM_ALLOWED_PAGE_HOSTS
                or not parsed.path.startswith("/event/") or len(event_url) > 1000):
            stats['invalid_event_url'] += 1
            return None, None
        origin = f"{parsed.scheme}://{parsed.netloc.lower()}"
        if origin not in robots_cache:
            robots_cache[origin] = get_robots(event_url)
        rp = robots_cache[origin]
        if rp is None:
            stats['robots_unavailable'] += 1
            return None, None
        if not rp.can_fetch(UA, event_url):
            stats['robots_disallowed'] += 1
            return None, None
        try:
            response = SESSION.get(event_url, timeout=18, allow_redirects=False)
            if response.status_code != 200:
                stats['http_unavailable'] += 1
                return None, None
            if len(response.content) > 3_000_000:
                stats['too_large'] += 1
                return None, None
            if 'html' not in response.headers.get('Content-Type', 'text/html').lower():
                stats['not_html'] += 1
                return None, None
            low, high = tm_page_price(response.text)
            if low is None:
                stats['html_without_ticket_price'] += 1
            else:
                stats['public_page_price_found'] += 1
            return low, high
        except requests.RequestException as exc:
            stats['http_request_error'] += 1
            print(f"TM stránka: nelze načíst ({type(exc).__name__})")
            return None, None


    def tm_enrich_prices(events: list[dict], today: str, api_key: str) -> None:
        """Fill missing Ticketmaster prices and explain *why* a price stayed empty."""
        from collections import Counter
        candidates = [e for e in events
                      if (str(e.get("id", "")).startswith("ticketmaster-")
                          and e.get("date", "") >= today
                          and tm_price_check_due(e, today))]
        candidates.sort(key=lambda e: (e.get("price") is not None, e.get("date", "9999")))
        checked = filled = page_filled = api_filled = 0
        robots_cache: dict = {}
        diagnostics = Counter()
        for e in candidates[:TM_MAX_PRICE_CHECKS_PER_RUN]:
            eid = str(e["id"])[len("ticketmaster-"):]
            low, high = tm_detail_price(eid, api_key)
            method = "Ticketmaster"
            if low is None:
                diagnostics['discovery_detail_without_price'] += 1
                low, high = tm_web_price(str(e.get("ticket_url") or ""), robots_cache, diagnostics)
                method = "Ticketmaster (stránka)"
                if low is not None:
                    page_filled += 1
            else:
                api_filled += 1
            e["tm_price_checked_at"] = today
            checked += 1
            if low is not None:
                if e.get("price") is None or e.get("price_source") in ("Ticketmaster", "Ticketmaster (stránka)"):
                    was_missing = e.get("price") is None
                    e["price"], e["price_max"], e["price_source"] = low, high, method
                    e["price_checked_at"] = today
                    e["price_from"] = True
                    if was_missing:
                        filled += 1
            time.sleep(0.25)
        missing_total = sum(1 for e in events if str(e.get("id", "")).startswith("ticketmaster-") and e.get("price") is None)
        print(f"TM CENY: prověřeno {checked}, nově doplněno {filled}, z veřejné stránky {page_filled}, "
              f"zbývá bez ceny {missing_total}, celkem čeká na další kontrolu {max(0,len(candidates)-checked)}")
        # Public log contains no keys, full event URLs, cookies, or private data.
        print("TM DIAGNOSTIKA: " + ", ".join(f"{k}={diagnostics[k]}" for k in (
            'discovery_detail_without_price', 'public_page_price_found',
            'robots_disallowed', 'robots_unavailable', 'http_unavailable',
            'html_without_ticket_price', 'invalid_event_url', 'too_large',
            'not_html', 'http_request_error')))
        print(f"TM ZDROJE: API={api_filled}, veřejná stránka={page_filled}")


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
                        tm_set_sale_phase(previous, item)
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
                    tm_set_sale_phase(candidate, item)
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



    # Inventory Status API provides *actual* primary ticket price ranges, including CZ.
    # This is a restricted API: enable ONLY if Ticketmaster approved access and supplied
    # a separate Inventory Status key. Never scrape seating charts or bypass a bot block.
    TM_INVENTORY_ENDPOINT = 'https://app.ticketmaster.com/inventory-status/v1/availability'


    def parse_inventory_price(row: dict) -> tuple[int | None, int | None]:
        """Extract an available primary ticket range in CZK. Exclude resale offers.

        The API caps maximum prices at 2000 and uses `listingsExtendBeyondMax` to
        signal clipping. When capped, do not publish a misleading maximum.
        """
        if not isinstance(row, dict) or str(row.get('currency', '')).upper() != 'CZK':
            return None, None
        if row.get('status') not in ('TICKETS_AVAILABLE', 'FEW_TICKETS_LEFT'):
            return None, None
        values = []
        for offer in row.get('priceRanges') or []:
            if not isinstance(offer, dict) or str(offer.get('type', '')).lower() != 'primary':
                continue
            try:
                low = float(offer['minPrice'])
                high = float(offer['maxPrice'])
                if (not all(map(math.isfinite, (low, high)))
                        or not 0 < low <= high <= 200_000):
                    continue
                values.append((low, high, bool(offer.get('listingsExtendBeyondMax'))))
            except (KeyError, ValueError, TypeError, OverflowError):
                pass
        if not values:
            return None, None
        low = round(min(x[0] for x in values))
        max_is_capped = any(x[2] for x in values)
        high = None if max_is_capped else round(max(x[1] for x in values))
        return low, high


    def tm_inventory_enrich(events: list[dict], today: str, key: str) -> None:
        """Optional authorized source. Continue safely if access is missing/denied."""
        if not key:
            print('TM inventory: není zapnuté (vyžaduje samostatně schválený API přístup)')
            return
        eligible = [e for e in events
                    if str(e.get('id', '')).startswith('ticketmaster-')
                    and str(e.get('date', '')) >= today
                    and (e.get('price') is None or e.get('price_source') in
                         ('Ticketmaster', 'Ticketmaster (stránka)', 'Ticketmaster Inventory Status API'))]
        # One batch of 60 per run, fill all missing prices progressively without
        # spending all requests on already-verified prices.
        eligible.sort(key=lambda e: (e.get('price') is not None, e.get('date', '9999')))
        batch = eligible[:60]
        if not batch:
            print('TM inventory: nic ke kontrole')
            return
        ids = [str(e['id']).removeprefix('ticketmaster-') for e in batch]
        if any(not re.fullmatch(r'[A-Za-z0-9_-]{3,80}', eid) for eid in ids):
            print('TM inventory: neplatné ID, krok přeskočen')
            return
        try:
            response = SESSION.post(TM_INVENTORY_ENDPOINT,
                                    params={'events': ','.join(ids), 'apikey': key},
                                    timeout=24)
            if response.status_code in (401, 403):
                print('TM inventory: přístup zamítnut (HTTP %s); vyžádej si schválení Ticketmasteru' % response.status_code)
                return
            if response.status_code != 200:
                print('TM inventory: momentálně nedostupné (HTTP %s)' % response.status_code)
                return
            rows = response.json()
            if not isinstance(rows, list):
                print('TM inventory: neočekávaná odpověď; data nezměněna')
                return
        except (requests.RequestException, ValueError, TypeError) as exc:
            print('TM inventory: chyba odpovědi %s; data nezměněna' % type(exc).__name__)
            return
        prices_by_id = {str(r.get('eventId', r.get('eventid', ''))): r
                        for r in rows if isinstance(r, dict)}
        filled = changed = 0
        for e in batch:
            row = prices_by_id.get(str(e['id']).removeprefix('ticketmaster-'))
            lo, hi = parse_inventory_price(row)
            if lo is None:
                continue
            was_missing = e.get('price') is None
            if (e.get('price'), e.get('price_max'), e.get('price_source')) != (lo, hi, 'Ticketmaster Inventory Status API'):
                e['price'] = lo
                e['price_max'] = hi
                e['price_from'] = True
                e.pop('price_note', None)
                e['price_source'] = 'Ticketmaster Inventory Status API'
                e['price_checked_at'] = today
                changed += 1
                filled += int(was_missing)
        print(f'TM inventory: {len(batch)} kontrolováno, {filled} doplněno, {changed} aktualizováno')


    def apply_price_overrides(events: list[dict]) -> None:
        """Human-verified section prices; never mistake one sector for the lowest seat."""
        try:
            data = json.loads(EVENT_FILE.read_text(encoding='utf-8')).get('price_overrides', {})
        except (OSError, ValueError) as exc:
            print('CENY override: neplatný JSON: ' + str(type(exc).__name__), file=sys.stderr)
            return
        if not isinstance(data, dict):
            print('CENY override: očekává se objekt ID -> cena', file=sys.stderr)
            return
        count = 0
        for e in events:
            row = data.get(e.get('id'))
            if not isinstance(row, dict):
                continue
            try:
                price = int(row['price'])
                maximum = row.get('price_max')
                maximum = int(maximum) if maximum is not None else None
                if price < 0 or price > 200_000 or (maximum is not None and not price <= maximum <= 200_000):
                    raise ValueError('Mimo rozsah')
            except (TypeError, ValueError, KeyError):
                print('CENY override: chybná cena ID: '+str(e.get('id'))[:100], file=sys.stderr)
                continue
            label = str(row.get('section') or '').strip()
            if len(label) > 60 or any(ord(ch)<32 for ch in label):
                print('CENY override: chybný název sektoru', file=sys.stderr)
                continue
            e['price'] = price
            e['price_max'] = maximum
            e['price_from'] = bool(row.get('confirmed_minimum', False))
            if label:
                e['price_note'] = label
            else:
                e.pop('price_note', None)
            e['price_source'] = 'Ruční ověření vstupenky'
            if row.get('checked_at'):
                e['price_checked_at'] = str(row['checked_at'])[:10]
            count += 1
        print(f'CENY override: {count} ručně ověřených cen aplikováno')


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
            # Inventory pricing/status is handled in _build_tickets() after import,
            # avoiding a duplicate API request for the same event IDs.
        apply_price_overrides(events)
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
    # Small pure helpers are exposed for offline regression testing.
    main.tm_page_price = tm_page_price
    main.tm_sale_phase = tm_sale_phase
    main.tm_price = tm_price
    main.tm_set_sale_phase = tm_set_sale_phase
    return main

# ========================================================================
# PRICES + AVAILABILITY
# ========================================================================
def _build_tickets():
    #!/usr/bin/env python3
    """UKA: conservative ticket sales/availability/price enrichment.

    Runs AFTER scripts/update_events.py. Does not require modifications to the
    existing concert importer and never treats missing info as sold out.
    Only Ticketmaster's authorized Inventory Status API can verify primary inventory.
    Discovery supplies sales *phase* (not seat availability).
    Official O2 pages supply explicitly advertised public-sale notices.
    """

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
            print('TM Inventory: schválený API klíč CHYBÍ; ceny zbývajících kategorií a dostupnost nelze ověřit.')
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
    return main

# ========================================================================
# PUBLIC PRICE SEARCH
# ========================================================================
def _build_public_prices():
    #!/usr/bin/env python3
    """UKA: carefully enrich missing CZK prices from public event details.

    No access to a Ticketmaster seat map is attempted. Website robots directives
    are respected, including 403/unavailable robots (fail closed). This updater
    only reads linked/explicitly indexed event pages and does not claim to
    know live ticket inventory. It never overwrites a nonempty price.

    Run AFTER update_events.py and sync_ticket_info.py:
        python scripts/find_public_prices.py
        python scripts/find_public_prices.py --dry-run

    The events.json field "price_links" contains *confirmed event detail links*.
    Rotating public GoOut catalogue pages are inspected automatically to avoid
    entering hundreds of URLs by hand. Coverage is partial and best-effort.
    Such links are matched to events by title, exact date and venue. The script
    also tries event's own ticket_url when on the supported public sites.
    """
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
    REPORT_FILE = ROOT / 'price_check_report.json'
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
        try:
            raw = json.loads(EVENTS_FILE.read_text(encoding='utf-8')).get('price_catalog_cache', {})
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
        """Retained for API compatibility; written as part of events.json in run()."""
        return {'version': 1, 'entries': dict(sorted(entries.items())[:MAX_CACHE_ITEMS])}


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
        obj = json.loads(EVENTS_FILE.read_text('utf-8')).get('price_links', [])
        if not isinstance(obj, list):
            raise RuntimeError('events.json: pole price_links musí být JSON pole []')
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
                        evidence_type = 'ověřený veřejný údaj (datum v events.json.price_links)'
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
        # Store catalogue memory together with events; never leave a sidecar file.
        cache_before = data.get('price_catalog_cache', {})
        data['price_catalog_cache'] = persist_catalog_cache(report['catalog_cache'])
        if json.dumps(events, sort_keys=True, ensure_ascii=False) != before or data['price_catalog_cache'] != cache_before:
            data['updated_at'] = datetime.now().astimezone().isoformat(timespec='seconds')
            EVENTS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        return report
    return run



# ========================================================================
# EVENTLOOK: import and verified fallbacks (same consolidated script)
# ========================================================================
def _build_eventlook():
    #!/usr/bin/env python3
    """UKA Eventlook discovery + verified fallback. No invented venues or live stock."""
    import argparse
    import json
    import re
    import unicodedata
    from datetime import date, datetime, timedelta
    from difflib import SequenceMatcher
    from pathlib import Path
    from urllib.parse import urljoin, urlparse
    from urllib.robotparser import RobotFileParser
    from zoneinfo import ZoneInfo

    import requests
    from bs4 import BeautifulSoup

    ROOT = Path(__file__).resolve().parent.parent
    SOURCE = 'Eventlook'
    USER_AGENT = 'UKAEventCatalog/1.0 (+https://matias-danz.github.io/uka/; respect robots.txt)'
    ALLOWED_DOMAIN = 'www.eventlook.cz'
    LISTINGS = [
        'https://www.eventlook.cz/',
        'https://www.eventlook.cz/udalosti/?city=Praha',
        'https://www.eventlook.cz/udalosti/?city=Brno',
        'https://www.eventlook.cz/udalosti/?city=Plze%C5%88',
        'https://www.eventlook.cz/udalosti/?city=Ostrava',
        'https://www.eventlook.cz/udalosti/?city=Liberec',
        'https://www.eventlook.cz/udalosti/?city=Olomouc',
        'https://www.eventlook.cz/udalosti/?city=%C4%8Cesk%C3%A9%20Bud%C4%9Bjovice',
        'https://www.eventlook.cz/udalosti/?city=Karlovy%20Vary',
        'https://www.eventlook.cz/udalosti/?city=Pardubice',
        'https://www.eventlook.cz/udalosti/?city=Jind%C5%99ich%C5%AFv%20Hradec',
        'https://www.eventlook.cz/udalosti/?date=week',
        'https://www.eventlook.cz/udalosti/?sort=hot',
        'https://www.eventlook.cz/udalosti/?organizer=94',
    ]
    VENUES = {
        ('typos music club','brno'):(49.1971964,16.6091164,'Běhounská 22, Brno'),
        ('ox club prague','praha'):(50.0744873,14.4352169,'Francouzská 75/4, Praha'),
        ('klub k2','ceske budejovice'):(48.9751458,14.4698178,'Sokolský ostrov 462/1, České Budějovice'),
        ('radost fx','praha'):(50.07587,14.43199,'Bělehradská 234/120, Praha'),
        ('roxy','praha'):(50.09072,14.42588,'Dlouhá 33, Praha'),
        ('fuchs2','praha'):(50.09525,14.43668,'ostrov Štvanice, Praha'),
        ('distrikt','praha'):(50.087697,14.453446,'Tachovské náměstí 290/5, Praha 3'),
    }

    def norm(s):
        s=unicodedata.normalize('NFKD',str(s or '').casefold())
        s=''.join(c for c in s if not unicodedata.combining(c))
        return re.sub(r'[^a-z0-9]+',' ',s).strip()

    def base_city(city):
        c=norm(city)
        if c.startswith('praha') or c.startswith('hlavni mesto praha'):return 'praha'
        if c.startswith('brno'):return 'brno'
        return c

    def valid_location(lat,lng):
        try:return 48.5<=float(lat)<=51.1 and 12.0<=float(lng)<=19.0
        except (ValueError,TypeError):return False

    def date_ok(value):
        try:return bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}',str(value))) and date.fromisoformat(value)>=date.today()-timedelta(days=1)
        except ValueError:return False

    def slug_from_url(url):
        m=re.search(r'/(?:events|udalosti)/([^/?#]+)/?',url)
        return m.group(1) if m else None

    def safe_event_url(url):
        p=urlparse(url)
        return p.scheme=='https' and p.hostname==ALLOWED_DOMAIN and bool(slug_from_url(url))

    def is_duplicate(new, old):
        if new['id']==old.get('id'):return True
        if new.get('ticket_url') and new['ticket_url']==old.get('ticket_url'):return True
        if new['date']!=old.get('date'):return False
        if norm(new['venue']) != norm(old.get('venue','')):return False
        # Same headline and venue/date; do not merge unrelated parties at same venue.
        a,b=norm(new['title']),norm(old.get('title',''))
        return a==b or SequenceMatcher(None,a,b).ratio()>=.84

    def seed_record(row):
        slug=row.get('slug') or slug_from_url(row['ticket_url'])
        if not slug or not safe_event_url(row['ticket_url']) or not date_ok(row['date']):return None
        if row.get('lat') is not None and not valid_location(row.get('lat'),row.get('lng')):return None
        price=row.get('price')
        if price is not None and (not isinstance(price,(float,int)) or price<0):return None
        event={**row,'id':'eventlook-'+slug,'source':SOURCE+' – ověřený detail',
               'verified_at':'2026-10-20', 'image_url':row.get('image_url',''),
               'image_credit':'Eventlook / pořadatel',
               'price_source':'Eventlook – veřejný detail (ověřeno 20. 10. 2026)',
               'price_from':True}
        event.pop('slug',None)
        confirmed_cta=bool(event.pop('sale_cta_verified',False))
        if confirmed_cta:
            event.update(sales_phase='on_sale',sales_phase_checked_at='2026-10-20',
                         sales_phase_source='Eventlook – veřejně zobrazené tlačítko nákupu (kontrola 20. 10. 2026)')
        # No confirmation of remaining stock! Buy button itself is not inventory.
        return event

    def robot_rules(session):
        try:
            r=session.get('https://www.eventlook.cz/robots.txt',timeout=12)
            if r.status_code!=200:
                return None, 'robots.txt nedostupný / HTTP '+str(r.status_code)
            robots=RobotFileParser()
            robots.parse(r.text.splitlines())
            return robots,None
        except requests.RequestException as ex:
            return None,'robots.txt není dostupný: '+type(ex).__name__

    def allowed(robots,url):
        return robots is not None and robots.can_fetch(USER_AGENT,url)

    def catalog_links(html,base):
        soup=BeautifulSoup(html,'html.parser')
        found=set()
        for a in soup.select('a[href]'):
            url=urljoin(base,a.get('href','')).split('#')[0]
            if safe_event_url(url):found.add(url)
        return sorted(found)

    def jsonld_events(soup):
        arr=[]
        def walk(node):
            if isinstance(node,list):
                for x in node:walk(x)
            elif isinstance(node,dict):
                t=node.get('@type',[])
                if t=='Event' or (isinstance(t,list) and 'Event' in t):arr.append(node)
                for value in node.values():
                    if isinstance(value,(list,dict)):walk(value)
        for tag in soup.find_all('script',type='application/ld+json'):
            try:walk(json.loads(tag.string or tag.get_text()))
            except (ValueError,TypeError):pass
        return arr

    def build_venue_map(existing_events):
        venues=dict(VENUES)
        for event in existing_events:
            if not event.get('venue') or not event.get('city'):
                continue
            if not valid_location(event.get('lat'),event.get('lng')):
                continue
            key=(norm(event['venue']),base_city(event['city']))
            if key not in venues:
                venues[key]=(float(event['lat']),float(event['lng']),str(event.get('address') or ''))
        return venues


    def extract_live_event(html,url,venue_map=None):
        if venue_map is None:venue_map=VENUES
        if not safe_event_url(url):return None
        soup=BeautifulSoup(html,'html.parser')
        heading=soup.find('h1')
        if not heading:return None
        title=heading.get_text(' ',strip=True)
        if not title:return None
        for e in jsonld_events(soup):
            if norm(e.get('name'))==norm(title):
                ld=e;break
        else:ld={}
        start=str(ld.get('startDate',''))
        if re.match(r'\d{4}-\d{2}-\d{2}',start):
            day=start[:10];tm=start[11:16] if len(start)>=16 else ''
        else:
            head=soup.get_text(' ',strip=True)[:1100]
            m=re.search(r'(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d{2})\s*[·\s]+(\d{1,2}):(\d{2})',head)
            if not m:return None
            day=f'{m.group(3)}-{int(m.group(2)):02}-{int(m.group(1)):02}'
            tm=f'{int(m.group(4)):02}:{m.group(5)}'
        if not date_ok(day):return None
        text=soup.get_text(' ',strip=True)
        # Related events at the end of Eventlook's detail page have their own prices.
        # Never treat those prices as the entry fee for the current event.
        lead=text.split('Další události',1)[0]
        header=lead[:1100]
        free_explicit=bool(re.search(
            r'\b(?:vstup(?:né)?\s+zdarma|vstup\s+je\s+zdarma|zdarma\s+vstup|cena\s*[:：]\s*(?:zdarma|0\s*Kč))\b',
            header[:600],re.I))
        location=ld.get('location',{}) if isinstance(ld.get('location'),dict) else {}
        venue=location.get('name','')
        addr=location.get('address',{})
        city=addr.get('addressLocality','') if isinstance(addr,dict) else ''
        # The Eventlook h1 is normally followed by a venue and city near the price.
        if not venue or not city:
            near=text.split(title,1)[1][:500] if title in text else header[:500]
            nearby_norm=norm(near)
            for (v,c) in sorted(venue_map,key=lambda row:len(row[0]),reverse=True):
                if v and v in nearby_norm and c in nearby_norm:
                    venue=venue or next((ev for ev in ['Typos music club','OX Club Prague','Klub K2','Radost FX','Roxy','Fuchs2','Distrikt'] if norm(ev)==v),v)
                    city=city or ('České Budějovice' if c=='ceske budejovice' else c.capitalize())
                    break
        # Extract venue/city from the visible event header if structured data is absent.
        if not venue or not city:
            head_text = soup.get_text(' ', strip=True)[:750]
            # Eventlook places `Venue, City` just after the date on detail pages.
            mloc = re.search(r'\d{4}\s*[·\-]\s*\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}\s+([^,]{2,85}),\s*([^,]{2,65})\s+(?:od\s+\d|\d[\d\s]*\s*[-–]\s*\d)',head_text, re.I)
            if mloc:
                venue=venue or mloc.group(1).strip()
                city=city or mloc.group(2).strip()
        # Skip non-CZ locations; do not mistake Bratislava for Czechia.
        FOREIGN_CITIES = {'bratislava','kosice','banska bystrica','trnava','zilina','presov','nitra','vienna','wien','berlin'}
        if any(base_city(city).startswith(x) for x in FOREIGN_CITIES) or not venue or not city: return None
        key=(norm(venue),base_city(city))
        coords=venue_map.get(key)

        if coords:
            lat,lng,address=coords
        else:
            # Unknown venues belong in the list; never invent coordinates for the map.
            lat,lng,address=None,None,(addr.get('streetAddress','') if isinstance(addr,dict) else '')
            # Source page's own navigation link can include exact coordinates.
            from urllib.parse import parse_qs
            for link in soup.select('a[href]'):
                dest=parse_qs(urlparse(link.get('href','')).query).get('destination',[''])[0]
                hit=re.fullmatch(r'\s*(-?\d{1,3}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)\s*',dest)
                if hit and valid_location(*hit.groups()):
                    lat,lng=map(float,hit.groups())
                    break
        # If the page lacks coordinates, only accept a city already seen in CZ data.
        if lat is None and base_city(city) not in {c for _, c in venue_map}:
            return None
        # Price from structured offers, or from price header near the event title.
        minimum=maximum=None
        offers=ld.get('offers',[])
        if isinstance(offers,dict):offers=[offers]
        for o in offers:
            if isinstance(o,dict) and str(o.get('priceCurrency','CZK')).upper()=='CZK':
                try:
                    val=float(o.get('lowPrice',o.get('price')))
                    # Eventlook may report 0 as an unset/schema placeholder.
                    # Free admission must also be explicitly stated in the event detail.
                    if val==0 and not free_explicit:continue
                    if 0<=val<200000:minimum=int(val) if minimum is None else min(minimum,int(val))
                    mx=o.get('highPrice')
                    if mx is not None and float(mx)>=val:maximum=int(float(mx))
                except (ValueError,TypeError):pass
        if minimum is None:
            # Only read the event's own heading, never the description or recommended listings.
            near_title=header.split(title,1)[-1][:230] if title in header else header[:230]
            pm=re.search(r'(?:od|from)\s*(\d[\d\s\u00a0]{0,8})\s*Kč',near_title,re.I)
            if pm:minimum=int(re.sub(r'\D','',pm.group(1)))
            rng=re.search(r'(\d[\d\s\u00a0]{0,8})\s*[-–]\s*(\d[\d\s\u00a0]{0,8})\s*Kč',near_title)
            if rng:
                left,right=(int(re.sub(r'\D','',v)) for v in rng.groups())
                if 0<=left<=right<200000:minimum=minimum if minimum is not None else left;maximum=right
            if minimum is None and free_explicit:minimum=0
        if minimum is not None and not (0<=minimum<200000):minimum=maximum=None
        meta=soup.find('meta',property='og:image')
        photo=meta.get('content','') if meta else ''
        if not photo.startswith('https://'):photo=''
        result={'id':'eventlook-'+slug_from_url(url),'title':title,'artist':'DJ line-up' if re.search(r'halloween|party|rave|dj',norm(title),re.I) else title,
            'category':'klub' if re.search(r'\bkiss (?:or |and )?slap\b',norm(title)) else 'rave' if 'rave' in norm(title) else 'klub' if re.search(r'halloween|party|night',norm(title),re.I) else 'koncert',
            'venue':venue,'city':city,'address':address,'lat':lat,'lng':lng,
            'date':day,'time':tm,'price':minimum,'price_max':maximum,
            'price_from':minimum is not None and minimum>0,
            'price_free_verified':bool(minimum==0 and free_explicit),
            'price_source':'Eventlook – veřejný detail' if minimum is not None else '',
            'ticket_url':url,'source':'Eventlook','verified_at':date.today().isoformat(),
            'description':'Událost z programu Eventlook. Před návštěvou ověř termín u pořadatele.',
            'image_url':photo,'image_credit':'Eventlook / pořadatel'}
        # Important: CTA means open sales process, NOT verified remaining tickets.
        sold=re.search(r'Událost je vyprodána|VYPRODÁNO|Sold out',header[:450],re.I)
        cta=soup.find(lambda tag:tag.name in ('a','button') and re.search(r'^(Koupit vstupenky|Zakoupit|Buy tickets)$',tag.get_text(' ',strip=True),re.I))
        if sold:
            result.update(availability_status='sold_out',availability_source=SOURCE+' – detail',availability_verified_at=datetime.now(ZoneInfo('Europe/Prague')).isoformat(timespec='seconds'))
        elif cta:
            result.update(sales_phase='on_sale',sales_phase_checked_at=datetime.now(ZoneInfo('Europe/Prague')).isoformat(timespec='seconds'),sales_phase_source=SOURCE+' – tlačítko nákupu (bez ověření volných míst)')
        return result

    def merge_events(current,new_records):
        merged=list(current);added=0;refreshed=0
        for n in new_records:
            if not n or not date_ok(n['date']):continue
            index=next((i for i,x in enumerate(merged) if is_duplicate(n,x)),None)
            if index is None:
                merged.append(n);added+=1
            else:
                old=merged[index]
                # Do not erase manual prices; only fill when unknown.
                updates={k:v for k,v in n.items() if k in ('sales_phase','sales_phase_checked_at','sales_phase_source','availability_status','availability_source','availability_verified_at') and v}
                for k in ('price','price_max','image_url'):
                    if old.get(k) in (None,'') and n.get(k) not in (None,''):updates[k]=n[k]
                for k in ('price_source','price_from','price_free_verified'):
                    if 'price' in updates and n.get(k) is not None:updates[k]=n[k]
                if updates:
                    combined={**old,**updates}
                    if combined!=old:merged[index]=combined;refreshed+=1
        return merged,added,refreshed


    EVENTLOOK_VERIFIED=[{'slug': 'halloween-typos-brno-cimhcf', 'title': 'HALLOWEEN – TYPOS BRNO', 'date': '2026-10-23', 'time': '22:00', 'venue': 'Typos music club', 'city': 'Brno', 'address': 'Běhounská 22, Brno', 'lat': 49.1971964, 'lng': 16.6091164, 'price': 189, 'price_max': 249, 'ticket_url': 'https://www.eventlook.cz/events/halloween-typos-brno-cimhcf/', 'category': 'klub', 'artist': 'DJ line-up', 'description': 'Halloweenská klubová párty s DJ a tematickým programem.', 'sale_cta_verified': False}, {'slug': 'halloween-typos-brno-lzwidy', 'title': 'HALLOWEEN – TYPOS BRNO (Part 2)', 'date': '2026-10-27', 'time': '22:00', 'venue': 'Typos music club', 'city': 'Brno', 'address': 'Běhounská 22, Brno', 'lat': 49.1971964, 'lng': 16.6091164, 'price': 189, 'price_max': 249, 'ticket_url': 'https://www.eventlook.cz/events/halloween-typos-brno-lzwidy/', 'category': 'klub', 'artist': 'DJ line-up', 'description': 'Halloween Brno Part 2, speciální DJ party.', 'sale_cta_verified': True}, {'slug': 'welcome-to-hawkins-ox-wrbwro', 'title': 'WELCOME TO HAWKINS HALLOWEEN – OX', 'date': '2026-10-23', 'time': '21:00', 'venue': 'OX Club Prague', 'city': 'Praha', 'address': 'Francouzská 75/4, Praha', 'lat': 50.0744873, 'lng': 14.4352169, 'price': 250, 'price_max': 550, 'ticket_url': 'https://www.eventlook.cz/events/welcome-to-hawkins-ox-wrbwro/', 'category': 'klub', 'artist': 'DJ line-up', 'description': 'Halloweenská party s hip-hopem, R&B a mainstreamem.', 'sale_cta_verified': True}, {'slug': 'silly-spooky-halloween-npnfeh', 'title': 'SILLY SPOOKY HALLOWEEN – OX', 'date': '2026-10-24', 'time': '21:00', 'venue': 'OX Club Prague', 'city': 'Praha', 'address': 'Francouzská 75/4, Praha', 'lat': 50.0744873, 'lng': 14.4352169, 'price': 250, 'price_max': 550, 'ticket_url': 'https://www.eventlook.cz/udalosti/silly-spooky-halloween-npnfeh/', 'category': 'klub', 'artist': 'DJ line-up', 'description': 'Studentská halloweenová party v OX Prague.', 'sale_cta_verified': False}, {'slug': 'scary-movie-halloween-brdwmc', 'title': 'SCARY MOVIE HALLOWEEN – OX', 'date': '2026-10-30', 'time': '21:00', 'venue': 'OX Club Prague', 'city': 'Praha', 'address': 'Francouzská 75/4, Praha', 'lat': 50.0744873, 'lng': 14.4352169, 'price': 250, 'price_max': 700, 'ticket_url': 'https://www.eventlook.cz/en/events/scary-movie-halloween-brdwmc/', 'category': 'klub', 'artist': 'DJ line-up', 'description': 'Horror party s mainstreamem, hip-hopem a R&B.', 'sale_cta_verified': True}, {'slug': 'welcome-ox-halloween-3110-vcqsmn', 'title': 'WELCOME OX HALLOWEEN – 31. 10.', 'date': '2026-10-31', 'time': '21:00', 'venue': 'OX Club Prague', 'city': 'Praha', 'address': 'Francouzská 75/4, Praha', 'lat': 50.0744873, 'lng': 14.4352169, 'price': 299, 'price_max': 399, 'ticket_url': 'https://www.eventlook.cz/pl/events/welcome-ox-halloween-3110-vcqsmn/', 'category': 'klub', 'artist': 'DJ line-up', 'description': 'Halloweenská hudební party v OX Prague.', 'sale_cta_verified': True}, {'slug': 'halloween-wjcfya', 'title': 'HALLOWEEN – Klub K2', 'date': '2026-10-30', 'time': '21:00', 'venue': 'Klub K2', 'city': 'České Budějovice', 'address': 'Sokolský ostrov 462/1, České Budějovice', 'lat': 48.9751458, 'lng': 14.4698178, 'price': 200, 'price_max': 300, 'ticket_url': 'https://www.eventlook.cz/udalosti/halloween-wjcfya/', 'category': 'klub', 'artist': 'DJ line-up', 'description': 'Halloween party: mainstream, rap a techno na dvou scénách.', 'sale_cta_verified': True}, {'slug': 'onebig-halloween-qtpltb', 'title': 'ONEBIG HALLOWEEN – Radost FX', 'date': '2026-10-30', 'time': '22:00', 'venue': 'Radost FX', 'city': 'Praha', 'address': 'Bělehradská 234/120, Praha', 'lat': 50.07587, 'lng': 14.43199, 'price': 360, 'price_max': 1500, 'ticket_url': 'https://www.eventlook.cz/udalosti/onebig-halloween-qtpltb/', 'category': 'klub', 'artist': 'DJ line-up', 'description': 'Halloween s hip-hopem, afrobeats, R&B a dancehallem.', 'sale_cta_verified': True}, {'slug': 'tuya-rave-x-halloween-kwecut', 'title': 'TUYA RAVE x HALLOWEEN', 'date': '2026-10-31', 'time': '22:00', 'venue': 'Distrikt', 'city': 'Praha', 'address': 'Tachovské náměstí 290/5, Praha 3', 'lat': 50.087697, 'lng': 14.453446, 'price': 450, 'price_max': 2550, 'ticket_url': 'https://www.eventlook.cz/events/tuya-rave-x-halloween-kwecut/', 'category': 'rave', 'artist': 'DJs / hard techno lineup', 'description': 'Dvě stage, hard techno, halloweenová edice.', 'sale_cta_verified': True}, {'slug': 'halloween-rave-fuchs-2-vkoiks', 'title': 'HALLOWEEN RAVE – FUCHS2', 'date': '2026-10-29', 'time': '21:00', 'venue': 'Fuchs2', 'city': 'Praha', 'address': 'ostrov Štvanice, Praha 7', 'lat': 50.09525, 'lng': 14.43668, 'price': 250, 'price_max': 350, 'ticket_url': 'https://www.eventlook.cz/udalosti/halloween-rave-fuchs-2-vkoiks/', 'category': 'rave', 'artist': 'DJ line-up', 'description': 'Halloweenský studentský rave na Štvanici.', 'sale_cta_verified': True}, {'slug': 'k-halloween-2026-trick-or-treat-vcieda', 'title': 'K-Halloween 2026 || Trick or Treat', 'date': '2026-10-31', 'time': '22:00', 'venue': 'Tabarin Club Brno', 'city': 'Brno', 'address': 'Divadelní 603/3, Brno', 'lat': 49.1948086, 'lng': 16.6142313, 'price': 150, 'price_max': 600, 'ticket_url': 'https://www.eventlook.cz/udalosti/k-halloween-2026-trick-or-treat-vcieda/', 'category': 'klub', 'artist': 'K-pop DJ night', 'description': 'Ověřená hudební událost na Eventlooku; údaje a prodej ověř před návštěvou.', 'sale_cta_verified': True}, {'slug': 'bieberchella-typos-brno-nmklpl', 'title': 'BIEBERCHELLA – TYPOS BRNO', 'date': '2026-11-06', 'time': '22:00', 'venue': 'Typos music club', 'city': 'Brno', 'address': 'Běhounská 22, Brno', 'lat': 49.1971964, 'lng': 16.6091164, 'price': 169, 'price_max': 229, 'ticket_url': 'https://www.eventlook.cz/udalosti/bieberchella-typos-brno-nmklpl/', 'category': 'klub', 'artist': 'DJ line-up', 'description': 'Ověřená hudební událost na Eventlooku; údaje a prodej ověř před návštěvou.', 'sale_cta_verified': True}, {'slug': 'kiss-or-slap-typos-brno-bkjwjb', 'title': 'KISS OR SLAP – TYPOS BRNO', 'date': '2026-11-27', 'time': '22:00', 'venue': 'Typos music club', 'city': 'Brno', 'address': 'Běhounská 22, Brno', 'lat': 49.1971964, 'lng': 16.6091164, 'price': 159, 'price_max': 199, 'ticket_url': 'https://www.eventlook.cz/udalosti/kiss-or-slap-typos-brno-bkjwjb/', 'category': 'klub', 'artist': 'DJ line-up', 'description': 'Ověřená hudební událost na Eventlooku; údaje a prodej ověř před návštěvou.', 'sale_cta_verified': True}, {'slug': 'hard-rico-show-typos-brno-dsjied', 'title': 'HARD RICO FOCUS TOUR – BRNO', 'date': '2026-12-05', 'time': '21:00', 'venue': 'Typos music club', 'city': 'Brno', 'address': 'Běhounská 22, Brno', 'lat': 49.1971964, 'lng': 16.6091164, 'price': 489, 'price_max': 1499, 'ticket_url': 'https://www.eventlook.cz/udalosti/hard-rico-show-typos-brno-dsjied/', 'category': 'koncert', 'artist': 'Hard Rico', 'description': 'Ověřená hudební událost na Eventlooku; údaje a prodej ověř před návštěvou.', 'sale_cta_verified': True}, {'slug': 'studentsky-halloween-roxy-wfrncy', 'title': 'NEJVĚTŠÍ STUDENTSKÝ HALLOWEEN – ROXY', 'date': '2026-10-31', 'time': '21:00', 'venue': 'ROXY', 'city': 'Praha', 'address': 'Dlouhá 33, Praha', 'lat': 50.09072, 'lng': 14.42588, 'price': 250, 'price_max': 650, 'ticket_url': 'https://www.eventlook.cz/udalosti/studentsky-halloween-roxy-wfrncy/', 'category': 'klub', 'artist': 'DJ line-up', 'description': 'Ověřená hudební událost na Eventlooku; údaje a prodej ověř před návštěvou.', 'sale_cta_verified': True}]

    def correct_known_blowup_price(events):
        """Correct the reported wrong free entry for the uniquely identified Blowup #05."""
        changed=0
        for event in events:
            url=str(event.get('ticket_url') or '').lower()
            exact_url=slug_from_url(url)=='blowup-05-lolaiv'
            # Also handle event records imported earlier under a different source id.
            exact_event=(event.get('date')=='2026-10-23' and
                         norm(event.get('title')) in ('blowup 05','blowup 5','blowup 5 robin zoot') and
                         'sasazu' in norm(event.get('venue')) and
                         base_city(event.get('city'))=='praha')
            if not (exact_url or exact_event):continue
            if (event.get('price')==450 and event.get('price_from') is True and
                    event.get('price_max') is None):continue
            # Reported directly by the UKA administrator, not scraped/independently
            # verified from a public price list. Keep that provenance visible.
            event['price']=450
            event['price_max']=None
            event['price_from']=True
            event['price_source']='Oprava ceny sdělená správcem UKA (23. 10. 2026)'
            event['price_checked_at']='2026-10-23'
            changed+=1
        return changed

    def main(dry_run=False, no_web=False):
        """Update the shared events.json with verified and allowed Eventlook sources."""
        path=ROOT/'events.json'
        payload=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(payload.get('events'),list):raise RuntimeError('events.json nemá pole events')
        verified=EVENTLOOK_VERIFIED
        candidates=[x for row in verified if (x:=seed_record(row))]
        print('EVENTLOOK: ověřených výchozích akcí:',len(candidates))
        discovered=0;not_mapped=0;catalogues_ok=0;urls=set()
        previous_cursor = int(payload.get('eventlook_cursor', 0) or 0)
        next_cursor=previous_cursor
        if not no_web:
            with requests.Session() as sess:
                sess.headers.update({'User-Agent':USER_AGENT,'Accept-Language':'cs-CZ,cs;q=0.9'})
                robots,reason=robot_rules(sess)
                if reason:print('EVENTLOOK: ONLINE import nepovolen/nelze ověřit –',reason)
                else:
                    for catalog in LISTINGS:
                        if not allowed(robots,catalog):continue
                        try:
                            r=sess.get(catalog,timeout=9)
                            if r.status_code==200 and 'text/html' in r.headers.get('Content-Type','text/html'):
                                urls.update(catalog_links(r.text,catalog));catalogues_ok+=1
                            else:print('EVENTLOOK KATALOG:',r.status_code,catalog)
                        except requests.RequestException as exc:
                            print('EVENTLOOK KATALOG nedostupný:',type(exc).__name__)
                    print(f'EVENTLOOK: katalogů načteno {catalogues_ok}, unikátních URL {len(urls)}')
                    venue_map=build_venue_map(payload['events']+candidates)
                    # Rotate through catalog URLs across hourly runs rather than
                    # rechecking the first 60 links forever.
                    all_urls=sorted(urls)
                    to_check=[]
                    if all_urls:
                        start=previous_cursor%len(all_urls)
                        to_check=(all_urls[start:]+all_urls[:start])[:35]
                        next_cursor=(start+len(to_check))%len(all_urls)
                    for url in to_check:
                        if not allowed(robots,url):continue
                        try:
                            r=sess.get(url,timeout=9)
                            if r.status_code!=200 or 'html' not in r.headers.get('Content-Type','text/html'):continue
                            item=extract_live_event(r.text,url,venue_map=venue_map)
                            if item:candidates.append(item);discovered+=1
                            else:not_mapped+=1
                        except requests.RequestException:continue
        merged,added,refreshed=merge_events(payload['events'],candidates)
        # Correct imported and legacy KISS OR SLAP events in every city, including Znojmo.
        categorized=0
        for ev in merged:
            if (re.search(r'\bkiss (?:or |and )?slap\b',norm(ev.get('title')))
                    and ev.get('category')!='klub'):
                ev['category']='klub'
                categorized+=1
        if categorized:
            refreshed+=categorized
            print(f'EVENTLOOK KATEGORIE: {categorized} akcí Kiss or Slap změněno na Kluby')
        # A narrowly targeted correction for Blowup #05, not a generic price guess.
        # Manual changes stored in admin_overrides take precedence in index.html.
        corrected=correct_known_blowup_price(merged)
        refreshed+=corrected
        if corrected:print(f'EVENTLOOK CENY: Blowup #05 opraven na od 450 Kč ({corrected} záznamů)')
        # Clean legacy false 'free' labels originating from unconfirmed 0 offers.
        # An explicit free entry has price_free_verified=True. Admin overrides
        # are separate and continue to override the base price at render time.
        uncertain_free=0
        for ev in merged:
            if (ev.get('price')==0 and 'eventlook' in str(ev.get('source','')).lower()
                    and not ev.get('price_free_verified')):
                ev['price']=None
                ev['price_max']=None
                ev['price_from']=False
                ev['price_source']=''
                uncertain_free+=1
        if uncertain_free:
            refreshed+=uncertain_free
            print(f'EVENTLOOK CENY: {uncertain_free} neověřených nulových cen změněno na Cena neuvedena')
        print(f'EVENTLOOK: živě získáno {discovered}, nepřiřazených detailů {not_mapped}; nových {added}, aktualizovaných {refreshed}, celkem {len(merged)}')
        if dry_run:
            print('EVENTLOOK: TEST – data se nemění')
        elif added or refreshed or (next_cursor!=previous_cursor):
            payload['events']=sorted(merged,key=lambda x:(x['date'],x.get('time',''),x['title']))
            payload['eventlook_cursor']=next_cursor
            payload['updated_at']=datetime.now(ZoneInfo('Europe/Prague')).isoformat(timespec='seconds')
            path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print('EVENTLOOK: změny zapsány do events.json')
        return added,refreshed
    main.parse_detail=extract_live_event
    main.merge=merge_events
    main.venues=build_venue_map
    main.links=catalog_links
    return main


def main():
    p = argparse.ArgumentParser(description='UKA: jedna synchronizace místo tří skriptů')
    p.add_argument('--dry-run', action='store_true', help='Ceny z GoOutu jen ověřit, neukládat')
    p.add_argument('--offline-cleanup', action='store_true', help='Bez internetu: jen vyčistit staré akce')
    p.add_argument('--eventlook-seed-only', action='store_true', help='Jen ověřené Eventlook akce, bez síťových požadavků a dalších importů')
    p.add_argument('--eventlook-dry-run', action='store_true', help='Test Eventlook importu bez zápisu')
    args=p.parse_args()
    if args.eventlook_seed_only:
        _build_eventlook()(dry_run=args.eventlook_dry_run, no_web=True)
        return 0
    print('UKA CENY V5: spousti se sjednoceny skript scripts/uka_sync.py')
    importer=_build_importer()
    old_argv=sys.argv
    try:
        sys.argv=[old_argv[0]]+(['--offline-cleanup'] if args.offline_cleanup else [])
        importer()
    finally:
        sys.argv=old_argv
    if args.offline_cleanup:
        print('UKA: offline test dokončen.')
        return 0
    _build_tickets()()
    _build_eventlook()(dry_run=args.eventlook_dry_run, no_web=args.offline_cleanup)
    _build_public_prices()(args.dry_run)
    return 0


if __name__=='__main__':
    sys.exit(main())
