from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict

@dataclass
class Listing:
    portal: str
    portal_id: str
    url: str
    title: str = ""
    vin: Optional[str] = None
    price_pln: Optional[int] = None
    year: Optional[int] = None
    mileage_km: Optional[int] = None
    engine: Optional[str] = None
    power_hp: Optional[int] = None
    gearbox: Optional[str] = None
    origin: Optional[str] = None
    seller_claims: List[str] = field(default_factory=list)
    equipment: Dict[str, Optional[bool]] = field(default_factory=dict)
    published_at: Optional[str] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    status: str = "active"
    problematic: bool = False
    image_urls: List[str] = field(default_factory=list)
    source_snapshot: Optional[str] = None

    def to_dict(self):
        return asdict(self)
