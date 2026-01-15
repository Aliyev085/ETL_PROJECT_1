# /opt/Etl_server_project_1/src/bina/helper.py
# CLEAN GOOGLE-LEVEL HELPER UTILITIES FOR BINA.AZ
# -------------------------------------------------------
# Only universal helpers remain. All old card-text parsing
# functions removed because the new Selenium fast scraper
# uses direct HTML selectors (correct approach).
# -------------------------------------------------------
#helper.py file
from __future__ import annotations
import re
from typing import Optional


# ===========================================================
# CLEAN TEXT
# ===========================================================
def clean_text(t: str | None) -> str | None:
    """
    Normalize whitespace and lowercase the text.
    """
    if not t:
        return None
    return " ".join(t.split()).strip().lower()


# ===========================================================
# SAFE INT
# ===========================================================
def safe_int(s: str | None) -> Optional[int]:
    """
    Extract digits and convert to int.
    """
    if not s:
        return None
    s = re.sub(r"[^\d]", "", s)
    try:
        return int(s)
    except:
        return None


# ===========================================================
# SAFE FLOAT
# ===========================================================
def safe_float(s: str | None) -> Optional[float]:
    """
    Extract numerical float safely.
    """
    if not s:
        return None
    s = s.replace(",", ".")
    s = re.sub(r"[^0-9.]", "", s)
    try:
        return float(s)
    except:
        return None
