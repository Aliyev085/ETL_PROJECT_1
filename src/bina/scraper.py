from __future__ import annotations
import random
import time
import re
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .config import settings
from .models import Flat
from .helpers import to_int, to_decimal, to_utc_naive

# Regex to extract listing_id from href
LISTING_HREF_RE = re.compile(r"/items/(\d+)")


def _norm(s: str) -> str:
    """Lowercase + rough ASCII-ish normalization for Azerbaijani text."""
    s = (s or "").lower()
    repl = {
        "ə": "e", "ö": "o", "ü": "u", "ı": "i", "ğ": "g", "ç": "c", "ş": "s",
    }
    for k, v in repl.items():
        s = s.replace(k, v)
    return s


class SeleniumDriver:
    """Wrapper for Selenium browser that collects listing cards."""

    def __init__(self) -> None:
        opts = ChromeOptions()
        if settings.HEADLESS:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--blink-settings=imagesEnabled=false")
        opts.add_argument("--lang=az-AZ")
        opts.add_argument(
            "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        self.driver = webdriver.Chrome(options=opts)
        self.driver.set_page_load_timeout(45)

    # ---------- navigation ----------
    def get(self, url: str) -> None:
        """Open URL and wait until page body loads."""
        self.driver.get(url)
        WebDriverWait(self.driver, 25).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

    def _abs_url(self, href: str) -> str:
        return href if href.startswith("http") else f"https://bina.az{href}"

    def close(self) -> None:
        try:
            self.driver.quit()
        except Exception:
            pass

    def scroll_once(self) -> None:
        """Scroll down once with random cooldown."""
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(
            random.uniform(settings.SCROLL_COOLDOWN_MIN, settings.SCROLL_COOLDOWN_MAX)
        )

    # ---------- collection ----------
    def collect_cards(self) -> List[Tuple[int, str, object]]:
        """Return (listing_id, absolute_url, card_element)."""
        cards = self.driver.find_elements(By.CSS_SELECTOR, "div[data-cy='item-card']")
        out: List[Tuple[int, str, object]] = []
        seen = set()

        for card in cards:
            try:
                a = card.find_element(By.CSS_SELECTOR, "a[data-cy='item-card-link']")
                href = a.get_attribute("href") or a.get_attribute("data-href") or ""
                m = LISTING_HREF_RE.search(href)
                if not m:
                    continue
                lid = int(m.group(1))
                if lid in seen:
                    continue
                seen.add(lid)
                out.append((lid, self._abs_url(href), card))
            except Exception:
                continue

        return out

    # ---------- flags from card ----------
    def _flags_from_card_text(self, card_el) -> Tuple[bool, bool]:
        """
        Detect 'has_deed' and 'has_mortgage' directly from visible icons on the main page.
        """
        try:
            has_deed = bool(
                card_el.find_elements(
                    By.CSS_SELECTOR,
                    ".sc-c5977095-3.sc-c5977095-8.gIHtUF.kOWPkX"
                )
            )
            has_mortgage = bool(
                card_el.find_elements(
                    By.CSS_SELECTOR,
                    ".sc-c5977095-3.sc-c5977095-9.gIHtUF.fdcozp"
                )
            )
            return has_deed, has_mortgage
        except Exception:
            return False, False

    # ---------- parsing ----------
    def parse_card(self, lid: int, url: str, card_el) -> Flat:
        """Extract structured data from one listing card."""

        # --- Price ---
        price_azn: Optional[int] = None
        try:
            price_text = card_el.find_element(By.CSS_SELECTOR, ".price-container span").text
            price_azn = int(price_text.replace("\xa0", "").replace(" ", "").replace("AZN", ""))
        except Exception:
            pass

        # --- Location area ---
        location_area: Optional[str] = None
        try:
            location_area = card_el.find_element(By.CSS_SELECTOR, "span.wvfDA").text.strip()
        except Exception:
            pass

        # --- Rooms, Area, Floors ---
        rooms = area_sqm = floor_current = floor_total = None
        try:
            spans = card_el.find_elements(By.CSS_SELECTOR, "span.bPmmkN span")
            for text in [s.text for s in spans if s.text]:
                if "otaqlı" in text:
                    rooms = to_int("".join([c for c in text if c.isdigit()]))
                elif "m²" in text:
                    area_sqm = to_decimal(text.replace("m²", "").strip())
                elif "mərtəbə" in text and "/" in text:
                    parts = text.replace("mərtəbə", "").strip().split("/")
                    if len(parts) == 2:
                        floor_current, floor_total = to_int(parts[0]), to_int(parts[1])
        except Exception:
            pass

        # --- Price per sqm ---
        price_per_sqm = None
        if price_azn and area_sqm:
            try:
                price_per_sqm = round(price_azn / float(area_sqm))
            except Exception:
                pass

        # --- City + posted_at ---
        location_city: Optional[str] = None
        posted_at = None
        try:
            city_when = card_el.find_element(By.CSS_SELECTOR, "div[data-cy='city_when']").text.strip()
            if "," in city_when:
                parts = city_when.split(",", 1)
                location_city = parts[0].strip()
                time_part = parts[1].strip().lower()

                now = datetime.utcnow()
                if "bugün" in time_part:
                    match = re.search(r"(\d{1,2}):(\d{2})", time_part)
                    if match:
                        hh, mm = int(match.group(1)), int(match.group(2))
                        posted_at = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
                elif "dünən" in time_part:
                    match = re.search(r"(\d{1,2}):(\d{2})", time_part)
                    if match:
                        hh, mm = int(match.group(1)), int(match.group(2))
                        posted_at = (now - timedelta(days=1)).replace(hour=hh, minute=mm, second=0, microsecond=0)
                else:
                    # fallback to helper function
                    try:
                        posted_at = to_utc_naive(time_part)
                    except Exception:
                        posted_at = None
        except Exception:
            pass

        # --- Owner type ---
        owner_type: Optional[str] = None
        try:
            label = card_el.find_element(By.CSS_SELECTOR, "span[data-cy='product-label-agency']").text.strip()
            owner_type = "agent" if "agent" in label.lower() else "owner"
        except Exception:
            owner_type = "owner"

        # --- Title logic ---
        title = "Agent Elanı" if owner_type == "agent" else "Sahibkar Elanı"

        # --- Flags ---
        has_deed, has_mortgage = self._flags_from_card_text(card_el)

        # --- Build Flat object ---
        return Flat(
            listing_id=lid,
            url=url,
            title=title,
            price_azn=price_azn,
            price_per_sqm=price_per_sqm,
            rooms=rooms,
            area_sqm=area_sqm,
            floor_current=floor_current,
            floor_total=floor_total,
            location_area=location_area,
            location_city=location_city,
            owner_type=owner_type,
            has_mortgage=has_mortgage,
            has_deed=has_deed,
            posted_at=posted_at,
        )
        