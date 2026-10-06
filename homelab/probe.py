"""Acceptance probe, NOT a production market scanner.
Run from the user's Docker host. Does not write market state or push to GitHub.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import socket
import io
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup
from PIL import Image

PORTALS = {
    "otomoto": "https://www.otomoto.pl/osobowe/opel/insignia?search%5Bfilter_enum_generation%5D=gen-b-2017&search%5Bfilter_enum_fuel_type%5D=petrol&search%5Bfilter_enum_body_type%5D=estate&search%5Bfilter_float_price%3Ato%5D=65000",
    "olx": "https://www.olx.pl/motoryzacja/samochody/opel/q-insignia-b-kombi-benzyna/",
    "autoplac": "https://autoplac.pl/oferty/samochody-osobowe/opel/insignia/benzynowe",
}
CHALLENGES = ("verify you are human", "potwierdź, że jesteś człowiekiem", "access denied", "just a moment", "checking your browser", "unusual traffic")


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(url: str, portal: str, detail: bool = False) -> str | None:
    try:
        u = urlsplit(url)
        if u.scheme != "https" or u.username or u.password or u.port not in (None, 443):
            return None
        if u.hostname not in (portal + ".pl", "www." + portal + ".pl"):
            return None
        if detail:
            pat = r"/oferta/.*\d{4}-\d{4}-[A-Z]{2}/?$" if portal == "autoplac" else r"/oferta/.*-ID[0-9A-Za-z]+\.html$"
            if not re.search(pat, u.path):
                return None
        return urlunsplit((u.scheme, u.netloc, u.path, "" if detail else u.query, ""))
    except (ValueError, TypeError):
        return None


def listing_id(url: str) -> str | None:
    path = urlsplit(url).path
    m = re.search(r"-(ID[0-9A-Za-z]+)\.html$", path) or re.search(r"(\d{4}-\d{4}-[A-Z]{2})/?$", path)
    return m.group(1) if m else None


def classify(status: int | None, title: str, text: str, error: str | None = None) -> str:
    if error:
        s = error.lower()
        if any(x in s for x in ("name_not_resolved", "name resolution", "dns")):
            return "dns_error"
        if "timeout" in s or "timed out" in s:
            return "timeout"
        return "navigation_error"
    if status in (401, 403, 429):
        return f"http_{status}"
    if any(x in (title + " " + text[:5000]).lower() for x in CHALLENGES):
        return "challenge_page"
    if status in (404, 410):
        return "removal_signal_not_sale"
    if status is None or not 200 <= status < 300:
        return "unexpected_http"
    return "http_ok_content_not_yet_validated"


def objects(value):
    if isinstance(value, list):
        for item in value:
            yield from objects(item)
    elif isinstance(value, dict):
        yield value
        if "@graph" in value:
            yield from objects(value["@graph"])
        if "mainEntity" in value:
            yield from objects(value["mainEntity"])


def metadata(raw: str, url: str) -> dict:
    """Probe only: scoped JSON-LD evidence, not a replacement market parser."""
    soup = BeautifulSoup(raw, "html.parser")
    primary = []
    for node in soup.select('script[type="application/ld+json"]'):
        try:
            for item in objects(json.loads(node.get_text())):
                types = item.get("@type", [])
                if isinstance(types, str):
                    types = [types]
                if not set(types).intersection({"Car", "Vehicle", "Product"}):
                    continue
                owner = item.get("url") or item.get("@id")
                if owner and listing_id(owner) and listing_id(owner) != listing_id(url):
                    continue
                primary.append(item)
        except (ValueError, TypeError):
            pass
    # Multiple unbound products are ambiguous (e.g. recommendations). Do not pick the first.
    exact = [x for x in primary if listing_id(x.get("url") or x.get("@id") or "") == listing_id(url)]
    chosen = exact[0] if len(exact) == 1 else primary[0] if len(primary) == 1 else {}
    fields = {k: chosen[k] for k in ("name", "vehicleModelDate", "productionDate", "mileageFromOdometer", "fuelType", "bodyType", "vehicleTransmission") if k in chosen}
    offer = chosen.get("offers", {})
    if isinstance(offer, dict):
        fields["price"] = offer.get("price")
        fields["currency"] = offer.get("priceCurrency")
    imgs = chosen.get("image", [])
    if isinstance(imgs, str):
        imgs = [imgs]
    elif isinstance(imgs, dict):
        imgs = [imgs]
    urls = [x if isinstance(x, str) else x.get("url") or x.get("contentUrl") for x in imgs if isinstance(x, (dict, str))]
    meta = soup.select_one('meta[property="og:image"]')
    if meta and not urls:
        urls = [meta.get("content")]
    names = (chosen.get("name") or "").lower()
    # This is evidence of a structured detail page, NOT proof of fuel/body/price eligibility.
    parsed = "insignia" in names and fields.get("price") is not None and bool(fields.get("mileageFromOdometer"))
    return {"fields": fields, "structured_listing_found": parsed, "image_candidates": list(dict.fromkeys(x for x in urls if x)), "primary_objects": len(primary)}


def image_allowed(url: str, portal: str) -> bool:
    try:
        u = urlsplit(url)
        if u.scheme != "https" or u.username or u.password or u.port not in (None, 443):
            return False
        host = u.hostname or ""
        return host in (portal + ".pl", "www." + portal + ".pl") or host.endswith((".olxcdn.com", ".autoplac.pl", ".otomoto.pl"))
    except ValueError:
        return False


def discover(raw: str, url: str, portal: str) -> dict:
    soup = BeautifulSoup(raw, "html.parser")
    # Diagnostic discovery is deliberately not called complete market coverage.
    links = []
    for a in soup.select("a[href]"):
        u = canonical(urljoin(url, a["href"]), portal, detail=True)
        if u and u not in links:
            links.append(u)
    next_node = soup.select_one('a[rel="next"],a[data-testid="pagination-forward"],a[data-testid="pagination-next"],a[aria-label="Next"],a[aria-label="Następna strona"]')
    nxt = canonical(urljoin(url, next_node.get("href", "")), portal) if next_node else None
    return {"links": links, "next": nxt}


def seed_urls(repo: Path) -> dict:
    result = {p: [] for p in PORTALS}
    p = repo / "config/tracked_urls.json"
    if p.exists():
        raw = json.loads(p.read_text(encoding="utf-8"))
        for portal in result:
            for url in raw.get(portal, []):
                u = canonical(url, portal, True)
                if u and u not in result[portal]:
                    result[portal].append(u)
    # Prefer most recent explicit copies from the curated state, not search snippets.
    p = repo / "data/listings.json"
    if p.exists():
        raw = json.loads(p.read_text(encoding="utf-8"))
        vals = raw.values() if isinstance(raw, dict) else raw
        for row in vals:
            for cp in row.get("copies", []):
                portal = cp.get("portal")
                if portal not in result:
                    continue
                u = canonical(cp.get("url") or "", portal, True)
                if u and u not in result[portal]:
                    result[portal].append(u)
    return result


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def run(args) -> int:
    from playwright.sync_api import sync_playwright
    os.umask(0o077)
    out = Path(args.output) / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True)
    repo = Path(args.repo)
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8")) if args.config else {}
    searches = cfg.get("searches", PORTALS)
    seeds = cfg.get("samples", seed_urls(repo))
    report = {"type": "homelab_acceptance_probe", "started_at": utc(), "scope": "bounded_sample_not_full_scan", "market_database_changed": False, "portals": {}, "results": []}
    write_json(out / "report.json", report)

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True, chromium_sandbox=True)
        except Exception as exc:
            report.update(status="browser_start_failed", error=str(exc), finished_at=utc())
            write_json(out / "report.json", report)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 2
        for portal in PORTALS:
            context = browser.new_context(locale="pl-PL", timezone_id="Europe/Warsaw", viewport={"width": 1440, "height": 1000}, accept_downloads=False)
            # Allow ordinary public JS/CSS/CDNs; deny local/LAN targets, no stealth or CAPTCHA solving.
            dns_cache = {}; blocked_resources = set()
            def network_policy(route):
                u = urlsplit(route.request.url); host = (u.hostname or "").lower()
                if host not in dns_cache:
                    try:
                        addresses = socket.getaddrinfo(host, u.port or 443, type=socket.SOCK_STREAM)
                        dns_cache[host] = bool(addresses) and all(ipaddress.ip_address(a[4][0]).is_global for a in addresses)
                    except (OSError, ValueError):
                        dns_cache[host] = False
                if u.scheme in ("http", "https") and not u.username and not u.password and dns_cache[host]:
                    route.continue_()
                else:
                    blocked_resources.add(host)
                    route.abort()
            context.route("**/*", network_policy)
            group = {"pages_attempted": 0, "details_attempted": 0, "detail_http_ok": 0, "structured_details": 0, "images_saved": 0, "skipped_reason": None, "coverage_complete": False}
            report["portals"][portal] = group
            group["samples_requested"] = args.samples
            origin = f"https://www.{portal}.pl" if portal != "autoplac" else "https://autoplac.pl"
            robots = RobotFileParser()
            try:
                rr = context.request.get(origin + "/robots.txt", timeout=15000, max_redirects=0)
                group["robots_http"] = rr.status
                if rr.status == 200:
                    robots.parse(rr.text().splitlines())
                elif rr.status in (404, 410):
                    robots.parse([])
                else:
                    group["skipped_reason"] = "robots_unavailable_or_blocked"
                rr.dispose()
            except Exception as exc:
                group["skipped_reason"] = "robots_fetch_error: " + str(exc)[:600]
            if group["skipped_reason"]:
                write_json(out / "report.json", report); context.close(); continue
            page = context.new_page()

            def fetch(url, kind):
                stamp = utc(); rec = {"portal": portal, "kind": kind, "url": url, "started_at": stamp}
                folder = out / portal / (f"{len(report['results']):03d}_" + (listing_id(url) or "search"))
                folder.mkdir(parents=True)
                if not robots.can_fetch("InsigniaTracker", url):
                    rec["outcome"] = "robots_disallowed"; raw = ""
                else:
                    status = None; err = None
                    try:
                        page.goto("about:blank")
                        response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        status = response.status if response else None
                        page.wait_for_timeout(1500)
                    except Exception as exc:
                        err = str(exc)
                    try:
                        raw = page.content(); title = page.title(); visible = page.locator("body").inner_text(timeout=2000)
                    except Exception:
                        raw = ""; title = ""; visible = ""
                    rec.update(http_status=status, final_url=page.url, title=title, navigation_error=err, outcome=classify(status, title, visible, err))
                    if not err and not canonical(page.url, portal):
                        rec["outcome"] = "unexpected_redirect"
                    # Every raw page remains PRIVATE. Never upload this directory to a public repo.
                    (folder / "source.html").write_text(raw, encoding="utf-8")
                    rec["source_bytes"] = len(raw.encode("utf-8"))
                    rec["locally_blocked_resource_hosts"] = sorted(blocked_resources)
                    try:
                        page.screenshot(path=str(folder / "screen.png"), full_page=False, timeout=5000)
                        rec["screenshot_saved"] = True
                    except Exception as exc:
                        rec["screenshot_error"] = str(exc)[:300]
                    if rec["outcome"] == "http_ok_content_not_yet_validated" and kind == "detail":
                        meta = metadata(raw, url); rec["metadata"] = meta
                        rec["outcome"] = "structured_detail_unvalidated" if meta["structured_listing_found"] else "html_received_parser_not_validated"
                        rec["photos"] = []
                        for image_url in meta["image_candidates"][:args.images]:
                            entry = {"url": image_url, "saved": False}
                            if image_allowed(image_url, portal):
                                try:
                                    image = context.request.get(image_url, timeout=15000, max_redirects=0)
                                    entry["http_status"] = image.status
                                    if image.ok:
                                        data = image.body()
                                        if len(data) > 15_000_000:
                                            raise ValueError("image exceeds 15 MB limit")
                                        with Image.open(io.BytesIO(data)) as im:
                                            if im.width < 320 or im.height < 180:
                                                raise ValueError("icon or undersized image")
                                            ext = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}.get(im.format)
                                            if ext is None or im.width * im.height > 50_000_000:
                                                raise ValueError("unsupported or oversized image")
                                            im.verify()
                                        name = hashlib.sha256(data).hexdigest() + ext
                                        (folder / name).write_bytes(data)
                                        entry.update(saved=True, file=name, bytes=len(data))
                                    image.dispose()
                                except Exception as exc:
                                    entry["error"] = str(exc)[:400]
                            else:
                                entry["error"] = "image_host_not_allowed"
                            rec["photos"].append(entry)
                rec.update(finished_at=utc(), evidence_dir=str(folder.relative_to(out)))
                report["results"].append(rec); write_json(folder / "result.json", rec); write_json(out / "report.json", report)
                print(portal, kind, rec.get("http_status"), rec["outcome"], url, flush=True)
                time.sleep(3)
                return rec, raw

            seen = set(); found = []; u = canonical(searches.get(portal, ""), portal)
            stop = False
            while u and u not in seen and len(seen) < args.pages:
                seen.add(u); group["pages_attempted"] += 1
                rec, raw = fetch(u, "search")
                if rec["outcome"] != "http_ok_content_not_yet_validated":
                    stop = rec["outcome"] in ("http_401", "http_403", "http_429", "challenge_page", "robots_disallowed")
                    group["search_failure"] = rec["outcome"]; break
                disc = discover(raw, u, portal)
                found.extend(x for x in disc["links"] if x not in found)
                rec["discovery"] = disc; u = disc["next"]
            group.update(discovered_links=len(found), pagination_followed=len(seen), pagination_unfinished=bool(u), coverage_complete=False)
            # Use both discovered links and known detail URLs. A probe is a bounded sample only.
            candidates = list(dict.fromkeys(found[:2] + seeds.get(portal, []) + found[2:]))[:args.samples]
            candidates = [canonical(x, portal, True) for x in candidates]
            for url in filter(None, candidates):
                if stop:
                    group["skipped_reason"] = "portal_blocked_stop_no_bypass"; break
                group["details_attempted"] += 1
                rec, raw = fetch(url, "detail")
                group["detail_http_ok"] += rec["outcome"] in ("structured_detail_unvalidated", "html_received_parser_not_validated")
                group["structured_details"] += rec["outcome"] == "structured_detail_unvalidated"
                group["images_saved"] += sum(x["saved"] for x in rec.get("photos", []))
                stop = rec["outcome"] in ("http_401", "http_403", "http_429", "challenge_page", "robots_disallowed")
            group["probed_sample_only"] = True
            write_json(out / "report.json", report); context.close()
        browser.close()
    all_access = all(x["discovered_links"] > 0 and x["structured_details"] > 0 and x["images_saved"] > 0 for x in report["portals"].values() if "discovered_links" in x) and all("discovered_links" in x for x in report["portals"].values())
    report.update(finished_at=utc(), status="sample_access_observed_review_required" if all_access else "acceptance_failed", ready_for_unattended_scanning=False)
    write_json(out / "report.json", report)
    # Shareable report excludes source HTML, image URLs, session data, and embedded metadata.
    share = {k: v for k, v in report.items() if k != "results"}
    share["results"] = [{k: r.get(k) for k in ("portal","kind","url","http_status","outcome","navigation_error","evidence_dir")} for r in report["results"]]
    write_json(Path(args.output) / "report-share.json", share)
    print("\nPRIVATE EVIDENCE:", out, "\nSHAREABLE REPORT:", Path(args.output) / "report-share.json", "\nSTATUS:", report["status"], flush=True)
    return 0 if all_access else 2


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default="/repo")
    p.add_argument("--output", default="/output")
    p.add_argument("--config")
    p.add_argument("--samples", type=int, default=3, choices=range(1, 11))
    p.add_argument("--pages", type=int, default=2, choices=range(1, 6))
    p.add_argument("--images", type=int, default=2, choices=range(1, 6))
    raise SystemExit(run(p.parse_args()))
