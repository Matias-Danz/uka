#!/usr/bin/env python3
"""Fail-closed validation for UKA's tracked JSON data. No network calls."""
import json
import math
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 30 * 1024 * 1024
MAX_TEXT = 12000
MAX_EVENTS = 30000
FILES = ('events.json', 'admin_overrides.json', 'availability_overrides.json', 'price_overrides.json', 'price_links.json')


def read_json(filename):
    p = ROOT / filename
    if p.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f'{filename}: exceeds size limit')
    def unique_keys(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ValueError(f'{filename}: duplicate key {k!r}')
            out[k] = v
        return out
    def reject_constant(value):
        raise ValueError(f'{filename}: nonfinite number {value}')
    return json.loads(p.read_text(encoding='utf-8'), object_pairs_hook=unique_keys, parse_constant=reject_constant)


def text(value, field, maxlen=MAX_TEXT):
    if not isinstance(value, str) or len(value) > maxlen or any(ord(c) < 32 and c not in '\n\t' for c in value):
        raise ValueError(f'{field}: invalid text')


def url(value, field):
    if value in ('', None):
        return
    text(value, field, 2048)
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or '%' in parsed.netloc or any(c.isspace() for c in value):
        raise ValueError(f'{field}: must be safe HTTPS URL')


def event(e, prefix, partial=False):
    if not isinstance(e, dict):
        raise ValueError(f'{prefix}: not an object')
    if not partial:
        for field in ('id', 'title', 'date'):
            if not e.get(field):
                raise ValueError(f'{prefix}: missing {field}')
    for field in ('id', 'title', 'artist', 'venue', 'city', 'address', 'description', 'price_note', 'image_credit'):
        if field in e and e[field] is not None:
            text(e[field], f'{prefix}.{field}', 512 if field != 'description' else MAX_TEXT)
    if 'date' in e and e['date']:
        text(e['date'], f'{prefix}.date', 32)
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', e['date']):
            raise ValueError(f'{prefix}: invalid date format')
        from datetime import date
        date.fromisoformat(e['date'])
    for field in ('ticket_url', 'price_url', 'image_url'):
        if field in e and e[field] is not None:
            if field == 'image_url' and isinstance(e[field], str) and re.fullmatch(r'\./media/[A-Za-z0-9._-]+', e[field]):
                continue
            url(e[field], f'{prefix}.{field}')
    for field in ('lat', 'lng', 'price', 'price_max', 'price_from'):
        if field in e and e[field] is not None and e[field] != '':
            v = e[field]
            if isinstance(v, bool):
                if field == 'price_from':
                    continue
                raise ValueError(f'{prefix}.{field}: boolean not allowed')
            if isinstance(v, (int, float)):
                if not math.isfinite(v):
                    raise ValueError(f'{prefix}.{field}: nonfinite')
                if field.startswith('price') and not 0 <= v <= 10000000:
                    raise ValueError(f'{prefix}.{field}: out of range')
                if field == 'lat' and not -90 <= v <= 90:
                    raise ValueError(f'{prefix}.{field}: invalid latitude')
                if field == 'lng' and not -180 <= v <= 180:
                    raise ValueError(f'{prefix}.{field}: invalid longitude')
            elif not partial and field in ('lat', 'lng') and isinstance(v, str):
                # Imported sources may represent coordinates as strings.
                try:
                    f = float(v)
                    if not math.isfinite(f) or abs(f) > (90 if field == 'lat' else 180):
                        raise ValueError()
                except ValueError:
                    raise ValueError(f'{prefix}.{field}: invalid coordinate')
            elif field.startswith('price') and isinstance(v, str):
                # Source import may include non-numeric price labels.
                text(v, f'{prefix}.{field}', 128)
            else:
                raise ValueError(f'{prefix}.{field}: invalid type')


def validate():
    data = {name: read_json(name) for name in FILES}
    main = data['events.json']
    if not isinstance(main, dict) or not isinstance(main.get('events'), list) or len(main['events']) > MAX_EVENTS:
        raise ValueError('events.json: invalid events list')
    ids = set()
    for i, e in enumerate(main['events']):
        event(e, f'events[{i}]')
        if e['id'] in ids:
            raise ValueError(f'events.json: duplicate event id {e["id"]}')
        ids.add(e['id'])
    admin = data['admin_overrides.json']
    if not isinstance(admin, dict) or not isinstance(admin.get('overrides', {}), dict) or not isinstance(admin.get('custom_events', []), list):
        raise ValueError('admin_overrides.json: invalid structure')
    for key, item in admin.get('overrides', {}).items():
        text(key, 'override key', 256)
        if not isinstance(item, dict) or not isinstance(item.get('fields', {}), dict):
            raise ValueError(f'admin override {key}: invalid fields')
        event(item['fields'], f'admin override {key}', partial=True)
        if 'hidden' in item and not isinstance(item['hidden'], bool):
            raise ValueError(f'admin override {key}: invalid hidden flag')
    for i, e in enumerate(admin.get('custom_events', [])):
        event(e, f'custom_events[{i}]')
        if e['id'] in ids:
            raise ValueError(f'custom_events[{i}]: duplicate event id')
        ids.add(e['id'])
    availability = data['availability_overrides.json']
    if not isinstance(availability, dict) or not isinstance(availability.get('overrides', {}), dict):
        raise ValueError('availability_overrides.json: invalid structure')
    for key, value in availability['overrides'].items():
        text(key, 'availability key', 256)
        if not isinstance(value, dict):
            raise ValueError(f'availability {key}: not an object')
        if 'url' in value:
            url(value['url'], f'availability {key}.url')
        for field, v in value.items():
            if isinstance(v, str):
                text(v, f'availability {key}.{field}', 2048)
    if not isinstance(data['price_overrides.json'], dict):
        raise ValueError('price_overrides.json: must be JSON object')
    if not isinstance(data['price_links.json'], list):
        raise ValueError('price_links.json: must be JSON array')
    for i, item in enumerate(data['price_links.json']):
        if not isinstance(item, dict):
            raise ValueError(f'price_links[{i}]: must be object')
        for key in ('url', 'ticket_url', 'price_url'):
            if key in item: url(item[key], f'price_links[{i}].{key}')
    print(f'VALIDATED: {len(main["events"])} imported events, {len(admin.get("custom_events", []))} custom events; {len(FILES)} JSON files')


if __name__ == '__main__':
    validate()
