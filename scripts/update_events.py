#!/usr/bin/env python3
"""UKA public events updater.

Intentionally conservative: extracts event metadata only from the public official
O2 arena concert programme, checks robots.txt first, and NEVER invents events.
Reads public ticket-price ranges from the official O2 arena event detail pages.
Additional ticket services need a documented API/feed or explicit permission.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import time
import unicodedata
from datetime import datetime, date
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
        if not title or len(title) > 160:
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
    # Maps existing records so historic O2 entries can be enriched without duplication.
    by_url_date = {
        (canonical_url(e.get("ticket_url", "")), e.get("date")): e
        for e in events if e.get("ticket_url") and e.get("venue") == "O2 arena"
    }
    by_title_date = {
        (normalize_title(e.get("title", "")), e.get("date")): e
        for e in events if e.get("venue") == "O2 arena"
    }

    for spec in SOURCES:
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

        def enrich(event: dict, detail_html: str) -> None:
            if not event.get("image_url"):
                image = event_image(detail_html, event.get("ticket_url", spec["url"]))
                if image:
                    event["image_url"] = image
                    event["image_credit"] = "O2 arena / pořadatel"
            # Never overwrite an independently-entered price. Periodically refresh
            # only prices recorded by the automated O2 price extractor.
            if event.get("price") is None or event.get("price_source") == "O2 arena":
                price = event_price(detail_html)
                event["price_checked_at"] = today
                if price is not None:
                    event["price"], event["price_max"] = price
                    event["price_source"] = "O2 arena"
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
                if ((existing.get("price") is None or existing.get("price_source") == "O2 arena")
                        and needs_price_check(existing, today)) or not existing.get("image_url"):
                    html = detail(c["url"])
                    if html:
                        enrich(existing, html)
                continue

            slug = urlparse(c["url"]).path.strip("/").split("/")[-1]
            event = {
                "id": f"o2-auto-{slug}-{c['date']}",
                "title": c["title"], "artist": c["title"], "category": "koncert",
                "venue": spec["venue"], "city": spec["city"],
                "address": spec["address"], "lat": spec["lat"], "lng": spec["lng"],
                "date": c["date"], "time": c["time"],
                "price": None, "price_max": None,
                "ticket_url": c["url"], "source": spec["name"], "verified_at": today,
                "description": "Akce z oficiálního programu O2 areny. Ceny ověřuj u pořadatele.",
                "image_url": "", "image_credit": "",
            }
            html = detail(c["url"])
            if html:
                enrich(event, html)
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
                    or (event.get("price") is not None and event.get("price_source") != "O2 arena")):
                continue
            url = event.get("ticket_url", "")
            if not allowed_official_detail(url, spec):
                continue
            html = detail(url)
            if html:
                enrich(event, html)

        print(f"{spec['name']}: {found} new events; {requests_used} detail pages checked")
    return events, found


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
    # Delete passed events from saved published JSON; also filtered on the website immediately.
    events = [copy.deepcopy(e) for e in old_events if isinstance(e, dict) and e.get("date", "") >= today]
    past_count = len(old_events) - len(events)
    new_count = 0
    if not args.offline_cleanup:
        events, new_count = update_from_sources(events, today)
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
