import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .util import detect_vin, detect_equipment, parse_int
from .models import Listing


class FetchBlocked(RuntimeError):
    pass


def get(session, url, timeout=20):
    r = session.get(url, timeout=timeout, allow_redirects=True)
    if r.status_code in (401, 403, 429):
        raise FetchBlocked(f"HTTP {r.status_code}")
    return r


def _jsonld_objects(soup):
    out = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.get_text(strip=True)
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        stack = obj if isinstance(obj, list) else [obj]
        for item in stack:
            if isinstance(item, dict) and isinstance(item.get("@graph"), list):
                out.extend(x for x in item["@graph"] if isinstance(x, dict))
            elif isinstance(item, dict):
                out.append(item)
    return out


def _pick_jsonld(soup):
    objs = _jsonld_objects(soup)
    for obj in objs:
        typ = str(obj.get("@type", "")).lower()
        if any(x in typ for x in ("vehicle", "car", "product")) or "offers" in obj:
            return obj
    return objs[0] if objs else {}


def _first(patterns, text, flags=re.I):
    for pat in patterns:
        m = re.search(pat, text, flags)
        if m:
            return m.group(1)
    return None


def _detect_price(obj, text):
    offers = obj.get("offers") if isinstance(obj, dict) else None
    if isinstance(offers, list):
        offers = offers[0] if offers else None
    if isinstance(offers, dict):
        value = offers.get("price") or offers.get("lowPrice")
        parsed = parse_int(value)
        if parsed:
            return parsed
    raw = _first([
        r"(?:Cena|price)[^0-9]{0,20}([0-9][0-9\s.]{3,})\s*(?:PLN|zł)",
        r"([0-9][0-9\s.]{3,})\s*(?:PLN|zł)",
    ], text)
    return parse_int(raw)


def _detect_year(obj, text):
    for key in ("vehicleModelDate", "productionDate", "releaseDate", "dateVehicleFirstRegistered"):
        value = obj.get(key) if isinstance(obj, dict) else None
        if value:
            m = re.search(r"\b(20[0-3]\d|19\d{2})\b", str(value))
            if m:
                return int(m.group(1))
    raw = _first([r"Rok produkcji[^0-9]{0,12}(20[0-3]\d|19\d{2})", r"\b(20(?:1[7-9]|2[0-6]))\b"], text)
    return int(raw) if raw else None


def _detect_mileage(obj, text):
    mileage = obj.get("mileageFromOdometer") if isinstance(obj, dict) else None
    if isinstance(mileage, dict):
        parsed = parse_int(mileage.get("value"))
        if parsed:
            return parsed
    raw = _first([
        r"Przebieg[^0-9]{0,20}([0-9][0-9\s.]*)\s*km",
        r"([0-9][0-9\s.]*)\s*km\s*(?:Przebieg)?",
    ], text)
    return parse_int(raw)


def _detect_power(text):
    raw = _first([r"(?:Moc|power)[^0-9]{0,15}([0-9]{2,3})\s*(?:KM|HP)", r"([0-9]{2,3})\s*KM"], text)
    return parse_int(raw)


def _detect_gearbox(text):
    t = text.lower()
    if any(x in t for x in ("skrzynia biegów automatyczna", "automatyczna skrzynia", "automat", "automatic")):
        return "automatic"
    if any(x in t for x in ("skrzynia biegów manualna", "manualna skrzynia", "manual", "manualna")):
        return "manual"
    return None


def _detect_origin(text):
    raw = _first([r"Kraj pochodzenia\s*([A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż -]{2,30})"], text)
    return raw.strip() if raw else None


def _seller_claims(text):
    t = text.lower()
    candidates = {
        "bezwypadkowy": ("bezwypadkowy", "bezwypadkowa"),
        "serwisowany w ASO": ("serwisowany w aso", "serwisowana w aso", "pełna historia serwisowa"),
        "pierwszy właściciel": ("pierwszy właściciel", "1 właściciel", "i właściciel"),
        "salon Polska": ("salon polska", "krajowy", "samochód krajowy"),
        "uszkodzony": ("uszkodzony", "uszkodzona"),
    }
    return [label for label, terms in candidates.items() if any(term in t for term in terms)]


def _problematic(text):
    t = text.lower()
    hard_terms = [
        "pojazd uszkodzony", "samochód uszkodzony", "auto uszkodzone",
        "kopci na biało", "kopcenie na biało", "uszkodzony silnik",
        "silnik do naprawy", "skrzynia do naprawy", "nie odpala",
    ]
    return any(term in t for term in hard_terms)


def _image_urls(soup, obj, base_url):
    urls = []
    seen = set()
    def add(value):
        if isinstance(value, str):
            u = urljoin(base_url, value)
            if u.startswith("http") and u not in seen:
                seen.add(u); urls.append(u)
        elif isinstance(value, list):
            for x in value: add(x)
        elif isinstance(value, dict):
            add(value.get("url") or value.get("contentUrl"))

    if isinstance(obj, dict):
        add(obj.get("image"))
    for prop in (("property", "og:image"), ("name", "twitter:image")):
        for meta in soup.find_all("meta", attrs={prop[0]: prop[1]}):
            add(meta.get("content"))
    for tag in soup.find_all("img"):
        add(tag.get("src") or tag.get("data-src") or tag.get("data-lazy-src"))
    return urls


def parse_generic_detail(portal: str, portal_id: str, url: str, html: str) -> Listing:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    obj = _pick_jsonld(soup)
    title = str(obj.get("name") or "") if isinstance(obj, dict) else ""
    if not title:
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
    return Listing(
        portal=portal, portal_id=portal_id, url=url, title=title,
        vin=detect_vin(text), price_pln=_detect_price(obj, text),
        year=_detect_year(obj, text), mileage_km=_detect_mileage(obj, text),
        power_hp=_detect_power(text), gearbox=_detect_gearbox(text),
        origin=_detect_origin(text), seller_claims=_seller_claims(text),
        equipment=detect_equipment(text), problematic=_problematic(text),
        image_urls=_image_urls(soup, obj, url)[:50],
    )
