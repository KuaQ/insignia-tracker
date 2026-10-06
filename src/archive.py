import hashlib
import html as html_lib
import json
from pathlib import Path
from datetime import datetime, timezone

from .util import safe_id, ext_from_url


def snapshot_fingerprint(listing, html):
    stable = {
        "portal": listing.portal,
        "portal_id": listing.portal_id,
        "vin": listing.vin,
        "price_pln": listing.price_pln,
        "year": listing.year,
        "mileage_km": listing.mileage_km,
        "gearbox": listing.gearbox,
        "equipment": listing.equipment,
        "seller_claims": listing.seller_claims,
        "problematic": listing.problematic,
        "image_urls": listing.image_urls,
        "html_sha256": hashlib.sha256(html.encode("utf-8", errors="replace")).hexdigest(),
    }
    raw = json.dumps(stable, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def archive_listing(session, listing, html, root: Path, max_images=12):
    vehicle_id = safe_id(listing.portal, listing.portal_id, listing.vin)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = root / vehicle_id / stamp
    media = dest / "media"
    media.mkdir(parents=True, exist_ok=True)
    downloaded = []
    for i, url in enumerate(listing.image_urls[:max_images], 1):
        try:
            r = session.get(url, timeout=20, allow_redirects=True)
            ct = (r.headers.get("content-type") or "").lower()
            if r.ok and r.content and (ct.startswith("image/") or len(r.content) > 5000):
                ext = ext_from_url(url)
                p = media / f"{i:02d}{ext}"
                p.write_bytes(r.content)
                downloaded.append(str(p.relative_to(dest)))
        except Exception:
            pass

    fingerprint = snapshot_fingerprint(listing, html)
    data = listing.to_dict() | {"snapshot_fingerprint": fingerprint}
    (dest / "listing.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (dest / "source.html").write_text(html, encoding="utf-8", errors="replace")
    manifest = {
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "portal": listing.portal, "portal_id": listing.portal_id, "url": listing.url,
        "snapshot_fingerprint": fingerprint,
        "images_discovered": len(listing.image_urls),
        "images_requested_limit": max_images,
        "images_saved": len(downloaded),
        "image_files": downloaded,
        "completeness": "FULL" if listing.image_urls and len(downloaded) == min(len(listing.image_urls), max_images) else "PARTIAL",
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    img_html = "".join(f'<img src="{html_lib.escape(p)}" loading="lazy">' for p in downloaded)
    safe_title = html_lib.escape(listing.title or f"{listing.portal} {listing.portal_id}")
    safe_url = html_lib.escape(listing.url, quote=True)
    pretty = html_lib.escape(json.dumps(data, ensure_ascii=False, indent=2))
    card = f'''<!doctype html><html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe_title}</title><style>body{{font-family:system-ui,-apple-system,sans-serif;max-width:1100px;margin:32px auto;padding:0 16px;background:#f7f7f8;color:#171717}}main{{background:white;padding:24px;border-radius:18px;box-shadow:0 4px 20px #0001}}.gallery{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}img{{width:100%;border-radius:12px}}pre{{white-space:pre-wrap;background:#f1f1f3;padding:16px;border-radius:12px;overflow:auto}}a{{color:#2458d3}}</style>
<main><h1>{safe_title}</h1><p><a href="{safe_url}">Oryginalne ogłoszenie</a></p><div class="gallery">{img_html}</div><h2>Dane</h2><pre>{pretty}</pre></main></html>'''
    (dest / "index.html").write_text(card, encoding="utf-8")
    return dest, manifest
