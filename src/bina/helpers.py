from __future__ import annotations
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

NUM_RE = re.compile(r"(\d+(?:[.,]\d+)?)")

# ----- conversions -----

def to_decimal(s: str | None) -> Optional[float]:
    if not s:
        return None
    s = re.sub(r"[^0-9.,]", "", s).replace(",", ".").strip(".")
    try:
        return float(s)
    except Exception:
        return None

def to_int(s: str | None) -> Optional[int]:
    if s is None:
        return None
    try:
        return int(float(s))
    except Exception:
        return None

# ----- floors (e.g., "3/9 mərtəbə") -----

def parse_floors(text: str | None) -> Tuple[Optional[int], Optional[int]]:
    if not text:
        return None, None
    m = re.search(r"(\d+)\s*/\s*(\d+)", text)
    if not m:
        return None, None
    return to_int(m.group(1)), to_int(m.group(2))

# ----- location split -----

def split_location(raw: str | None) -> Tuple[Optional[str], Optional[str]]:
    if not raw:
        return None, None
    parts = [p.strip() for p in re.split(r"[—-]", raw) if p.strip()]
    if len(parts) >= 2:
        return parts[0], parts[-1]
    if "Bakı" in raw:
        return raw.replace("Bakı", "").strip(" ,—-"), "Bakı"
    return raw, None

# ----- owner type -----

def detect_owner_type(text: str | None) -> Optional[str]:
    if not text:
        return None
    t = text.casefold()
    if any(k in t for k in ["agent", "agentlik", "vasitəçi"]):
        return "agent"
    if any(k in t for k in ["sahib", "sahibinden", "sahibindən"]):
        return "owner"
    return None

# ----- booleans from tags/labels -----

def detect_flags(text: str | None) -> tuple[Optional[bool], Optional[bool], Optional[bool]]:
    if not text:
        return None, None, None
    t = text.casefold()
    is_renovated = any(k in t for k in ["təmirli", "temirli", "yenilənib", "yenilenib", "renovated"]) or None
    has_mortgage = any(k in t for k in ["ipoteka", "mortgage"]) or None
    has_deed = any(k in t for k in ["kupça", "kupca", "çıxarış", "cixarish", "deed"]) or None
    return is_renovated, has_mortgage, has_deed

# ----- posted_at → UTC naive -----

BAKU = ZoneInfo("Asia/Baku")

_RELATIVE = {
    "bugün": 0, "bu gün": 0, "today": 0,
    "dünən": -1, "dün": -1, "yesterday": -1,
}

def to_utc_naive(posted_text: str | None) -> Optional[datetime]:
    if not posted_text:
        return None
    t = posted_text.strip().casefold()

    # Relative
    for key, delta in _RELATIVE.items():
        if key in t:
            now_baku = datetime.now(BAKU)
            base = (now_baku + timedelta(days=delta)).replace(hour=12, minute=0, second=0, microsecond=0)
            return base.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    # Fallback: now
    now_baku = datetime.now(BAKU).replace(hour=12, minute=0, second=0, microsecond=0)
    return now_baku.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
