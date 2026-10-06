import hashlib
import re
from urllib.parse import urlparse

VIN_RE = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b", re.I)

EQUIPMENT_TERMS = {
    "agr": ["agr"],
    "heated_seats": ["podgrzewane fotele", "podgrzewany fotel"],
    "heated_steering": ["podgrzewana kierownica", "kierownica ogrzewana"],
    "heated_windshield": ["podgrzewana przednia szyba", "ogrzewana szyba przednia"],
    "rear_camera": ["kamera cofania", "kamera parkowania tył"],
    "camera_360": ["kamera 360", "360°"],
    "blind_spot": ["martwe pole", "blind spot"],
    "rcta": ["rcta", "ruch poprzeczny"],
    "acc": ["tempomat adaptacyjny", "aktywny tempomat", "acc"],
    "intellilux": ["intellilux", "matrix led", "matrix"],
    "hud": ["head-up", "head up", "hud"],
    "dic8": ["virtual cockpit", "wirtualne zegary", "dic 8"],
    "carplay": ["apple carplay", "carplay"],
    "android_auto": ["android auto"],
    "electric_tailgate": ["elektryczna klapa", "elektryczne otwieranie bagażnika"],
    "handsfree_tailgate": ["hands-free", "otwieranie nogą", "bezdotykowe otwieranie"],
    "keyless": ["keyless", "open&start", "bezkluczyk"],
    "traffic_signs": ["rozpoznawanie znaków", "traffic sign"],
    "park_assist": ["asystent parkowania", "park assist"],
    "panorama": ["panorama", "panoramiczny dach", "szyberdach"],
    "bose": ["bose"],
    "flexride": ["flexride", "elektroniczna regulacja zawieszenia"],
}

def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()

def detect_vin(text: str):
    m = VIN_RE.search(text or "")
    return m.group(0).upper() if m else None

def detect_equipment(text: str):
    t = normalize_text(text)
    return {k: any(term in t for term in terms) for k, terms in EQUIPMENT_TERMS.items()}

def safe_id(portal: str, portal_id: str, vin: str | None = None):
    if vin:
        return vin.upper()
    raw = f"{portal}:{portal_id}".encode()
    return hashlib.sha1(raw).hexdigest()[:14]

def ext_from_url(url: str) -> str:
    p = urlparse(url).path.lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        if p.endswith(ext):
            return ext
    return ".jpg"

def parse_int(value):
    if value is None:
        return None
    s = re.sub(r"[^0-9]", "", str(value))
    try:
        return int(s) if s else None
    except ValueError:
        return None
