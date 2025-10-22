from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Flat:
    listing_id: int
    url: str
    title: Optional[str]

    price_azn: Optional[int]
    price_per_sqm: Optional[int]
    rooms: Optional[int]
    area_sqm: Optional[float]

    floor_current: Optional[int]
    floor_total: Optional[int]

    location_area: Optional[str]
    location_city: Optional[str]

    owner_type: Optional[str]

    has_mortgage: Optional[bool]
    has_deed: Optional[bool]

    posted_at: Optional[datetime]  # naive UTC
