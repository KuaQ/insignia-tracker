import json
import re
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .fetch import get, parse_generic_detail, FetchBlocked
from .archive import archive_listing, snapshot_fingerprint
from .state import load_json, save_json, append_event
from .util import safe_id

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = json.loads((ROOT / "config/settings.json").read_text(encoding="utf-8"))
TRACKED = json.loads((ROOT / "config/tracked_urls.json").read_text(encoding="utf-8"))
DATA = ROOT / "data"
ARCHIVE = ROOT / "archive"

SEARCH_URLS = {
    "otomoto": "https://www.otomoto.pl/osobowe/opel/insignia?search%5Bfilter_enum_generation%5D=gen-b-2017&search%5Bfilter_enum_fuel_type%5D=petrol&search%5Bfilter_enum_body_type%5D=estate&search%5Bfilter_float_price%3Ato%5D=65000",
    "olx": "https://www.olx.pl/motoryzacja/samochody/opel/q-insignia-b-kombi-benzyna/",
    "autoplac": "https://autoplac.pl/oferty/samochody-osobowe/opel/insignia/benzynowe",
}
DETAIL_HOST_RULES = {
    "otomoto": ("otomoto.pl", "/osobowe/oferta/"),
    "olx": ("olx.pl", "/d/oferta/"),
    "autoplac": ("autoplac.pl", "/oferta/opel/insignia/"),
}

def discover_links(session, portal, url):
    r = get(session, url, SETTINGS["request_timeout_seconds"])
    if r.status_code >= 400:
        raise RuntimeError(f"HTTP {r.status_code}")
    soup = BeautifulSoup(r.text, "lxml")
    host_piece, path_piece = DETAIL_HOST_RULES[portal]
    links = set()
    for a in soup.find_all("a", href=True):
        u = urljoin(r.url, a["href"])
        if host_piece in u and path_piece in u:
            links.add(u.split("#", 1)[0])
    text = r.text.replace("\\/", "/").replace("&amp;", "&").replace("\u002F", "/")
    for u in re.findall(r'https?://[^"\' <>]+', text):
        if host_piece in u and path_piece in u:
            links.add(u.split("#", 1)[0])
    # Some SPA pages contain only relative detail URLs inside JSON.
    for rel in re.findall(r'["\']([^"\']*' + re.escape(path_piece) + r'[^"\']+)["\']', text):
        u = urljoin(r.url, rel)
        if host_piece in u and path_piece in u:
            links.add(u.split("#", 1)[0])
    return sorted(links)

def portal_id(portal, url):
    if portal in ("otomoto", "olx"):
        m = re.search(r"(ID[0-9A-Za-z]+)", url)
        return m.group(1) if m else url.rstrip("/").split("/")[-1]
    slug = url.rstrip("/").split("/")[-1]
    m = re.search(r"([0-9]{4}-[0-9]{4}-[A-Z]{2})$", slug, re.I)
    return m.group(1) if m else slug

def changed(prev, listing, html):
    current = snapshot_fingerprint(listing, html)
    return prev.get("snapshot_fingerprint") != current, current

def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": SETTINGS["user_agent"],
        "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.6",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Cache-Control": "no-cache",
    })
    state = load_json(DATA / "listings.json", {})
    summary = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "portals": {}, "new": 0, "changed": 0, "archived": 0,
        "blocked": [], "direct_checks": {}
    }

    for portal, search_url in SEARCH_URLS.items():
        discovered = []
        discovery_error = None
        try:
            discovered = discover_links(session, portal, search_url)
        except Exception as e:
            discovery_error = str(e)
            summary["blocked"].append(portal)

        seeded = TRACKED.get(portal, [])
        links = sorted(set(discovered) | set(seeded))
        summary["portals"][portal] = {
            "discovered_links": len(discovered),
            "seeded_links": len(seeded),
            "total_to_check": len(links),
        }
        if discovery_error:
            summary["portals"][portal]["discovery_error"] = discovery_error

        checked = 0
        ok = 0
        gone = 0
        blocked = 0
        errors = 0

        for link in links:
            checked += 1
            pid = portal_id(portal, link)
            try:
                r = get(session, link, SETTINGS["request_timeout_seconds"])
                if r.status_code in (404, 410):
                    gone += 1
                    append_event(DATA / "events.jsonl", {
                        "type": "portal_copy_gone", "portal": portal,
                        "portal_id": pid, "url": link, "http_status": r.status_code
                    })
                    continue
                if r.status_code >= 400:
                    raise RuntimeError(f"HTTP {r.status_code}")

                ok += 1
                listing = parse_generic_detail(portal, pid, link, r.text)
                key = safe_id(portal, pid, listing.vin)
                now = datetime.now(timezone.utc).isoformat()
                prev = state.get(key, {})
                listing.first_seen = prev.get("first_seen") or now
                listing.last_seen = now
                is_changed, fingerprint = changed(prev, listing, r.text)
                record = listing.to_dict() | {"snapshot_fingerprint": fingerprint}

                if not prev:
                    summary["new"] += 1
                    event_type = "first_seen"
                elif is_changed:
                    summary["changed"] += 1
                    event_type = "changed"
                else:
                    event_type = None

                if event_type:
                    dest, manifest = archive_listing(
                        session, listing, r.text, ARCHIVE,
                        SETTINGS["max_images_per_listing"]
                    )
                    append_event(DATA / "events.jsonl", {
                        "type": event_type, "key": key, "portal": portal,
                        "portal_id": pid, "url": link,
                        "archive": str(dest.relative_to(ROOT)),
                        "price_pln": listing.price_pln,
                        "mileage_km": listing.mileage_km,
                        "images_saved": manifest["images_saved"],
                    })
                    summary["archived"] += 1
                state[key] = record
            except FetchBlocked as e:
                blocked += 1
                append_event(DATA / "events.jsonl", {
                    "type": "blocked", "portal": portal, "portal_id": pid,
                    "reason": str(e), "url": link
                })
            except Exception as e:
                errors += 1
                append_event(DATA / "events.jsonl", {
                    "type": "error", "portal": portal, "portal_id": pid,
                    "reason": str(e), "url": link
                })

        summary["direct_checks"][portal] = {
            "checked": checked, "ok": ok, "gone": gone,
            "blocked": blocked, "errors": errors
        }

    save_json(DATA / "listings.json", state)
    save_json(DATA / "last_run.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
