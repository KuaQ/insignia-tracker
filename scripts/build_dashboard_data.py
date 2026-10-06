"""Build Pages from durable history + newer observations, never from demo rows.
No network requests, paid services or changes to the observation source files.
"""
import copy
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / 'data/recovered_history_2026-10-06.json'


def load(path, default):
    if not path.exists():
        return default
    # A corrupt source must fail visibly, not silently become an empty database.
    return json.loads(path.read_text(encoding='utf-8'))


def identity(portal, url):
    path = urlsplit(url or '').path
    if portal == 'otomoto':
        m = re.search(r'-(ID[0-9A-Za-z]+)\.html$', path)
    elif portal == 'autoplac':
        m = re.search(r'(\d{4}-\d{4}-[A-Z]{2})/?$', path)
    else:
        m = re.search(r'-(ID[0-9A-Za-z]+)\.html$', path)
    return m.group(1) if m else None


def source_link(portal, pid):
    if portal == 'otomoto' and re.fullmatch(r'ID[0-9A-Za-z]+', pid):
        return f'https://www.otomoto.pl/osobowe/oferta/opel-insignia-{pid}.html'
    return None  # Do not invent OLX or Autoplac slugs from IDs alone.


def recovered_payload(source):
    rows, events = {}, []
    for values in source['rows']:
        if len(values) != len(source['columns']):
            raise ValueError('Invalid historical row width')
        row = dict(zip(source['columns'], values))
        key = row['key']
        if key in rows:
            raise ValueError(f'Duplicate historical vehicle: {key}')
        row.update(copy.deepcopy(source['details'].get(key, {})))
        portal = 'autoplac' if key.startswith('AP') else 'olx' if key.startswith('OLX') else 'otomoto'
        pid = key[2:] if portal == 'autoplac' else key[3:] if portal == 'olx' else key
        row.update(portal=portal, portal_id=pid, data_source='chat_history',
                   last_reported_at=source['as_of'], verification='historical_not_rechecked')
        row.setdefault('url', source_link(portal, pid))
        row.setdefault('problematic', False)
        row.setdefault('description', 'W dostępnych raportach zachowano parametry, bez szczegółowego opisu wyposażenia.')
        row.setdefault('defects', [])
        row.setdefault('seller_claims', [])
        equipment = {k: True for k in row.get('equipment', [])}
        equipment.update({k: False for k in row.pop('equipment_absent', [])})
        row['equipment'] = equipment
        copies = [{'portal': portal, 'portal_id': pid, 'url': row.get('url'),
                   'price_pln': row['price_pln'], 'status': row['status']}]
        for cp in row.get('copies', []):
            p, ident, price, *status = cp
            copies.append({'portal': p, 'portal_id': ident, 'url': source_link(p, ident),
                           'price_pln': price, 'status': status[0] if status else row['status']})
        row['copies'] = copies
        row['title'] = f"{row['year']} · {row['engine']}" + (f" · {row['power_hp']} KM" if row.get('power_hp') else '')
        if row.get('first_seen'):
            events.append({'at': row['first_seen'], 'key': key, 'type': 'first_seen',
                           'portal': portal, 'source': 'chat_history'})
        rows[key] = row
    for event in source['events']:
        if event['key'] not in rows:
            raise ValueError(f"Unknown historical event target: {event['key']}")
        events.append(dict(event, source='chat_history'))
    return rows, events


def merge_newer(rows, raw):
    # Keep the historical baseline even if data/listings.json is accidentally empty.
    values = list(raw.values()) if isinstance(raw, dict) else raw
    if not isinstance(values, list):
        raise ValueError('listings.json must contain an object or list')
    aliases = {}
    for key, row in rows.items():
        for cp in row['copies']:
            aliases[(cp['portal'], cp['portal_id'])] = key
    for item in values:
        if not isinstance(item, dict):
            continue
        row = copy.deepcopy(item)
        key = row.get('key')
        if key not in rows:
            key = aliases.get((row.get('portal'), row.get('portal_id')), key)
        if not key:
            continue
        stamp = row.get('observed_at') or row.get('last_reported_at') or row.get('last_seen')
        # Test scrapes and unqualified records must not overwrite the curated history.
        if not stamp or row.get('data_source') not in ('verified_run', 'chat_tracker_run'):
            continue
        old = rows.get(key, {})
        if stamp[:10] < old.get('last_reported_at', '')[:10]:
            continue
        if old.get('status') == 'sold' and row.get('status') == 'active' and not row.get('return_evidence'):
            continue
        merged = {**old, **row, 'key': key, 'last_reported_at': stamp}
        merged['first_seen'] = min(filter(None, [old.get('first_seen'), row.get('first_seen')]), default=None)
        merged['equipment'] = {**old.get('equipment', {}), **row.get('equipment', {})}
        cp_map = {(c['portal'], c['portal_id']): c for c in old.get('copies', [])}
        for cp in row.get('copies', []):
            cp_map[(cp['portal'], cp['portal_id'])] = cp
        merged['copies'] = list(cp_map.values())
        rows[key] = merged


def add_archive_links(rows):
    """Link only exact portal IDs/URLs. Test parser values are not observations."""
    lookup = {}
    for row in rows.values():
        for cp in row['copies']:
            lookup[(cp['portal'], cp['portal_id'])] = row
            token = identity(cp['portal'], cp.get('url'))
            if token:
                lookup[(cp['portal'], token)] = row
    count = 0
    for path in sorted((ROOT / 'archive').glob('*/*/listing.json')):
        try:
            archived = load(path, {})
            portal, url = archived.get('portal'), archived.get('url', '')
            row = lookup.get((portal, identity(portal, url)))
            if not row:
                continue
            folder = path.parent.relative_to(ROOT).as_posix()
            row.setdefault('archives', []).append({
                'url': 'https://github.com/KuaQ/insignia-tracker/tree/main/' + quote(folder, safe='/'),
                'label': 'Archiwum testowe — zapisane pliki, dane parsera niezweryfikowane',
                'at': path.parent.name,
                'images_saved_reported': load(path.parent / 'manifest.json', {}).get('images_saved')
            })
            count += 1
        except (ValueError, OSError, TypeError):
            continue
    return count


def build(root=None):
    global ROOT, RECOVERY
    if root is not None:
        ROOT = Path(root)
        RECOVERY = ROOT / 'data/recovered_history_2026-10-06.json'
    source = load(RECOVERY, None)
    if not source:
        raise ValueError('Historical baseline missing; refusing empty deployment')
    rows, events = recovered_payload(source)
    merge_newer(rows, load(ROOT / 'data/listings.json', {}))
    event_file = ROOT / 'data/events.jsonl'
    if event_file.exists():
        for line in event_file.read_text(encoding='utf-8').splitlines():
            if line.strip():
                event = json.loads(line)
                if event.get('source') in ('verified_run', 'chat_tracker_run'):
                    events.append(event)
    unique_events = {json.dumps(e, ensure_ascii=False, sort_keys=True): e for e in events}
    events = sorted(unique_events.values(), key=lambda e: (e.get('at', ''), e.get('key', '')))
    for row in rows.values():
        row['history'] = [e for e in events if e.get('key') == row['key']]
        if row.get('first_seen'):
            end = row.get('status_date') or row['last_reported_at'][:10]
            row['days_observed'] = (datetime.fromisoformat(end) - datetime.fromisoformat(row['first_seen'])).days
    archive_count = add_archive_links(rows)
    payload = {
        'meta': {'generated_at': datetime.now(timezone.utc).isoformat(),
                 'as_of': max(r['last_reported_at'][:10] for r in rows.values()),
                 'note': source['provenance'], 'recovered_records': len(source['rows']),
                 'archive_snapshots_linked': archive_count},
        'listings': list(rows.values()), 'events': events
    }
    if len(payload['listings']) < 53:
        raise ValueError('Refusing to publish fewer than 53 recovered vehicles')
    out = ROOT / 'dashboard'
    out.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    (out / 'data.js').write_text('window.INSIGNIA_DATA = ' + text + ';\n', encoding='utf-8')
    (out / 'data.json').write_text(text + '\n', encoding='utf-8')
    print(f"Dashboard: {len(rows)} vehicles; {len(events)} events; {archive_count} archive links")
    return payload


if __name__ == '__main__':
    build()
