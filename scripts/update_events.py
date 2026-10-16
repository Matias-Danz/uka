#!/usr/bin/env python3
"""UKA public events updater.

Intentionally conservative: extracts event metadata only from the public official
O2 arena concert programme, checks robots.txt first, and NEVER invents events.
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


def normalize_title(title: str) -> str:
    """Use one stable normalized title to avoid an existing same-day venue duplicate."""
    value = unicodedata.normalize("NFKD", title).casefold()
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", value)


def update_from_sources(events: list[dict], today: str) -> tuple[list[dict], int]:
    found = 0
    index = {(canonical_url(e.get("ticket_url", "")), e.get("date")) for e in events if e.get("ticket_url")}
    names = {(normalize_title(e.get("title", "")), e.get("date")) for e in events if e.get("venue") == "O2 arena"}
    for spec in SOURCES:
        robot = get_robots(spec["url"])
        if robot is None:
            continue
        text = fetch(spec["url"], robot)
        if text is None:
            continue
        candidates = extract_program(text, spec)
        print(f"{spec['name']}: {len(candidates)} dated events in listing")
        if not candidates:
            print("WARNING: parser found no dated events, keeping previous data", file=sys.stderr)
            continue
        for c in candidates:
            if c["date"] < today or (c["url"], c["date"]) in index or (normalize_title(c["title"]), c["date"]) in names:
                continue
            # Only official O2 arena links are ingested from this feed.
            slug = urlparse(c["url"]).path.strip("/").split("/")[-1]
            detail = fetch(c["url"], robot)
            image = event_image(detail, c["url"]) if detail else ""
            event_id = f"o2-auto-{slug}-{c['date']}"
            events.append({
                "id": event_id,
                "title": c["title"],
                "artist": c["title"],
                "category": "koncert",
                "venue": spec["venue"],
                "city": spec["city"],
                "address": spec["address"],
                "lat": spec["lat"],
                "lng": spec["lng"],
                "date": c["date"],
                "time": c["time"],
                "price": None,
                "price_max": None,
                "ticket_url": c["url"],
                "source": spec["name"],
                "verified_at": today,
                "description": "Akce oznámená v oficiálním programu pořadatele. Cena a dostupnost se mohou změnit.",
                "image_url": image,
                "image_credit": "O2 arena / pořadatel" if image else "",
            })
            index.add((c["url"], c["date"]))
            names.add((normalize_title(c["title"]), c["date"]))
            found += 1
            # Reduce load on official programme web server.
            time.sleep(0.8)
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
