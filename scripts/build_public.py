#!/usr/bin/env python3
# UKA – prepare only public website files for GitHub Pages.
# Does not edit events.json, index.html or admin.html.
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist"

PUBLIC_EVENT_FIELDS = frozenset({
    "id", "title", "artist", "category", "venue", "city", "address",
    "lat", "lng", "date", "time", "price", "price_max", "price_from",
    "price_note", "source", "ticket_url", "image_url", "image_credit",
    "description", "verified_at", "sales_phase", "availability_status",
    "price_free_verified", "sale_cta_verified", "price_url",
})


def main():
    data = json.loads((ROOT / "events.json").read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("events"), list):
        raise ValueError("events.json must contain an events array")
    public_events = []
    for n, e in enumerate(data["events"]):
        if not isinstance(e, dict) or not e.get("id") or not e.get("title") or not e.get("date"):
            raise ValueError(f"Invalid event at index {n}")
        public_events.append({k: v for k, v in e.items() if k in PUBLIC_EVENT_FIELDS})
    public_data = {
        "updated_at": data.get("updated_at"),
        "events": public_events,
        # These fields are used by the current browser client to apply admin edits.
        # They include user-visible event metadata, never GitHub tokens.
        "admin_overrides": data.get("admin_overrides", {}),
        "availability_overrides": data.get("availability_overrides", {}),
    }
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    # The admin stays in the repository for its owner, not on the public Pages site.
    # Remove the public admin entry-point link, preserving the surrounding footer.
    index = re.sub(r'<a\b(?=[^>]*\bhref=["\']\./admin\.html["\'])[^>]*>.*?</a>',
                   '', index, flags=re.I | re.S)
    if OUT.exists():
        if OUT.is_symlink():
            raise ValueError("Refusing to delete a symlink dist folder")
        shutil.rmtree(OUT)
    OUT.mkdir()
    (OUT / "index.html").write_text(index, encoding="utf-8")
    (OUT / "events.json").write_text(
        json.dumps(public_data, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8")
    (OUT / ".nojekyll").touch()
    media = ROOT / "media"
    if media.is_dir():
        if any(p.is_symlink() for p in media.rglob("*")):
            raise ValueError("Symlinks in media/ are not allowed")
        shutil.copytree(media, OUT / "media")
    allowed = {"index.html", "events.json", ".nojekyll", "media"}
    got = {p.name for p in OUT.iterdir()}
    if got - allowed:
        raise AssertionError(f"Unexpected published file(s): {got - allowed}")
    print(f"UKA PUBLIC: {len(public_events)} events, {len((OUT / 'events.json').read_bytes())} bytes")
    print("UKA PUBLIC: website build excludes admin.html, scripts/, caches and secrets")


if __name__ == "__main__":
    main()
