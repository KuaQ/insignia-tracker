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
    if not links:
        text = r.text.replace("\\/", "/").replace("&amp;", "&")
        regex = re.compile(r'https?://[^"\' <>]+')
        for u in regex.findall(text):
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
    session.headers.update({"User-Agent": SETTINGS["user_agent"], "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.6"})
    state = load_json(DATA / "listings.json", {})
    summary = {"run_at": datetime.now(timezone.utc).isoformat(), "portals": {}, "new": 0, "changed": 0, "archived": 0, "blocked": []}

    for portal, search_url in SEARCH_URLS.items():
        try:
            links = discover_links(session, portal, search_url)
            summary["portals"][portal] = {"links": len(links)}
        except Exception as e:
            summary["portals"][portal] = {"error": str(e), "links": 0}
            summary["blocked"].append(portal)
            continue

        for link in links:
            pid = portal_id(portal, link)
            try:
                r = get(session, link, SETTINGS["request_timeout_seconds"])
                if r.status_code in (404, 410):
                    append_event(DATA / "events.jsonl", {"type": "portal_copy_gone", "portal": portal, "portal_id": pid, "url": link})
                    continue
                if r.status_code >= 400:
                    raise RuntimeError(f"HTTP {r.status_code}")

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
                    dest, manifest = archive_listing(session, listing, r.text, ARCHIVE, SETTINGS["max_images_per_listing"])
                    append_event(DATA / "events.jsonl", {
                        "type": event_type, "key": key, "portal": portal, "portal_id": pid,
                        "url": link, "archive": str(dest.relative_to(ROOT)),
                        "price_pln": listing.price_pln, "mileage_km": listing.mileage_km,
                        "images_saved": manifest["images_saved"],
                    })
                    summary["archived"] += 1
                state[key] = record
            except FetchBlocked as e:
                append_event(DATA / "events.jsonl", {"type": "blocked", "portal": portal, "portal_id": pid, "reason": str(e), "url": link})
            except Exception as e:
                append_event(DATA / "events.jsonl", {"type": "error", "portal": portal, "portal_id": pid, "reason": str(e), "url": link})

    save_json(DATA / "listings.json", state)
    save_json(DATA / "last_run.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
