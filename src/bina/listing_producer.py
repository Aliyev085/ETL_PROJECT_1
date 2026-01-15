#!/usr/bin/env python3
# FULLY FIXED LISTING PRODUCER FOR BINA.AZ (2025)
# ------------------------------------------------
# Based on ACTUAL HTML selectors provided
# ------------------------------------------------

from __future__ import annotations
import time
import re
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

from bina.config import settings
from bina.db import upsert_listing_fast
from bina.rabbit import RabbitMQ
from bina.helper import safe_int, clean_text


def get_driver():
    opts = Options()
    opts.binary_location = "/usr/bin/chromium"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--lang=az-AZ")
    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=opts)


# ----------------------------------------------------------
# ROBUST PARSERS - Handle dynamic class names
# ----------------------------------------------------------

def parse_price(card):
    """Price: <span class="...price-container"><span>280 000</span>"""
    try:
        el = card.find_element(By.CSS_SELECTOR, ".price-container span:first-child")
        return safe_int(el.text)
    except:
        pass
    # Fallback: find any span containing price pattern
    try:
        spans = card.find_elements(By.TAG_NAME, "span")
        for s in spans:
            txt = s.text.strip()
            if re.match(r"^\d[\d\s]{2,}$", txt):  # matches "280 000"
                return safe_int(txt)
    except:
        pass
    return None


def parse_rooms_area_floor(card):
    """
    All three are in spans containing: "X otaqlı", "X m²", "X/X mərtəbə"
    Also handles: "X sot" (land) → convert to m² (1 sot = 100 m²)
    Also handles: "X otaq" (rooms without 'ı')
    We search by TEXT PATTERN instead of fragile class names.
    """
    rooms, area, floor_c, floor_t = None, None, None, None
    
    try:
        spans = card.find_elements(By.TAG_NAME, "span")
        for s in spans:
            txt = s.text.strip().lower()
            
            # Rooms: "3 otaqlı" or "4 otaq"
            if ("otaqlı" in txt or "otaq" in txt) and rooms is None:
                m = re.search(r"(\d+)\s*otaq", txt)
                if m:
                    rooms = int(m.group(1))
            
            # Area: "136 m²"
            if "m²" in txt and area is None:
                m = re.search(r"(\d+)\s*m²", txt)
                if m:
                    area = int(m.group(1))
            
            # Area from SOT: "3 sot" → 300 m² (1 sot = 100 m²)
            if "sot" in txt and area is None:
                m = re.search(r"(\d+)\s*sot", txt)
                if m:
                    sot_value = int(m.group(1))
                    area = sot_value * 100  # Convert sot to m²
                    print(f"[PRODUCER] Converted {sot_value} sot → {area} m²")
            
            # Floor: "17/17 mərtəbə"
            if "mərtəbə" in txt and floor_c is None:
                m = re.search(r"(\d+)\s*/\s*(\d+)", txt)
                if m:
                    floor_c = int(m.group(1))
                    floor_t = int(m.group(2))
    except Exception as e:
        print(f"[PRODUCER] parse_rooms_area_floor error: {e}")
    
    return rooms, area, floor_c, floor_t


def parse_location(card):
    """
    Location area: span with class containing "sc-cb70b292-15" or text like "Xətai m."
    City: div[data-cy='city_when'] → "Bakı, dünən 17:18"
    """
    loc_area = None
    loc_city = None
    
    # Location area - try multiple approaches
    try:
        # Method 1: Known class
        el = card.find_element(By.CSS_SELECTOR, "[class*='sc-cb70b292-15']")
        loc_area = el.text.strip()
    except:
        pass
    
    if not loc_area:
        try:
            # Method 2: Look for span with metro/street pattern
            spans = card.find_elements(By.TAG_NAME, "span")
            for s in spans:
                txt = s.text.strip()
                # Skip if it's rooms/area/floor/price
                if any(x in txt for x in ["otaqlı", "m²", "mərtəbə", "000"]):
                    continue
                # Match location patterns: ends with m., r., q., k., etc.
                if re.search(r"\s+(m\.|r\.|q\.|k\.|küç\.|pr\.)$", txt) or "metro" in txt.lower():
                    loc_area = txt
                    break
        except:
            pass
    
    # City
    try:
        city_el = card.find_element(By.CSS_SELECTOR, "[data-cy='city_when']")
        city_raw = city_el.text.strip()
        loc_city = city_raw.split(",")[0].strip()
    except:
        pass
    
    return clean_text(loc_area), clean_text(loc_city)


def parse_badges(card):
    """
    IMPORTANT: On the LISTING PAGE, badges are just empty styled spans.
    The badge icons (.product-labels__i-icon--mortgage) are only on DETAIL pages.
    
    On listing cards:
    - .sc-cb70b292-8 = deed badge span (empty but styled)
    - .sc-cb70b292-9 = mortgage badge span (empty but styled)
    
    These spans exist but are EMPTY - we check if they have any visual indicator.
    Since they're CSS-styled, we check if element exists AND has content/width.
    """
    has_mortgage = False
    has_deed = False
    
    try:
        # Check mortgage badge
        mortgage_els = card.find_elements(By.CSS_SELECTOR, "[class*='sc-cb70b292-9']")
        for el in mortgage_els:
            # Check if element is visible (has dimensions)
            if el.size.get('width', 0) > 0 or el.size.get('height', 0) > 0:
                has_mortgage = True
                break
    except:
        pass
    
    try:
        # Check deed badge
        deed_els = card.find_elements(By.CSS_SELECTOR, "[class*='sc-cb70b292-8']")
        for el in deed_els:
            if el.size.get('width', 0) > 0 or el.size.get('height', 0) > 0:
                has_deed = True
                break
    except:
        pass
    
    return has_mortgage, has_deed


def detect_owner(card):
    """Agent badge: [data-cy='product-label-agency']"""
    try:
        card.find_element(By.CSS_SELECTOR, "[data-cy='product-label-agency']")
        return "agent"
    except:
        return "owner"


# ----------------------------------------------------------
# MAIN
# ----------------------------------------------------------
def main():
    limit = settings.FAST_SCRAPER_LIMIT
    rounds = settings.SCROLL_ROUNDS_LIMIT
    sleep = settings.SCROLL_SLEEP

    rabbit = RabbitMQ()
    driver = get_driver()

    print(f"[PRODUCER] START (limit={limit}, scroll_rounds={rounds})")

    driver.get(settings.BINA_BASE_URL)
    time.sleep(3)

    # SCROLL to load more
    last_height = 0
    for i in range(rounds):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(sleep)
        new_h = driver.execute_script("return document.body.scrollHeight;")
        print(f"[PRODUCER] Scroll {i+1}/{rounds}, height={new_h}")
        if new_h == last_height:
            break
        last_height = new_h

    cards = driver.find_elements(By.CSS_SELECTOR, "div[data-cy='item-card']")
    print(f"[PRODUCER] FOUND {len(cards)} CARDS")

    processed = 0
    errors = 0

    for idx, card in enumerate(cards):
        if processed >= limit:
            break

        try:
            a = card.find_element(By.CSS_SELECTOR, "a[data-cy='item-card-link']")
            url = a.get_attribute("href")
            match = re.search(r"/items/(\d+)", url)
            if not match:
                continue
            listing_id = match.group(1)
        except Exception as e:
            print(f"[PRODUCER] SKIP card {idx} — URL failed: {e}")
            errors += 1
            continue

        price = parse_price(card)
        rooms, area, floor_c, floor_t = parse_rooms_area_floor(card)
        loc_area, loc_city = parse_location(card)
        has_mortgage, has_deed = parse_badges(card)
        owner = detect_owner(card)

        # Debug output
        print(f"[PRODUCER] {listing_id}: price={price}, rooms={rooms}, area={area}, "
              f"floor={floor_c}/{floor_t}, loc={loc_area}, city={loc_city}, "
              f"mortgage={has_mortgage}, deed={has_deed}, owner={owner}")

        upsert_listing_fast(
            listing_id=listing_id,
            url=url,
            title="Elan",
            price_azn=price,
            area_sqm=area,
            price_per_sqm=(price / area if price and area else None),
            rooms=rooms,
            floor_current=floor_c,
            floor_total=floor_t,
            has_mortgage=has_mortgage,
            has_deed=has_deed,
            location_area=loc_area,
            location_city=loc_city,
            owned_type=owner,
            posted_at=datetime.utcnow(),
            scraped_at=datetime.utcnow(),
        )

        rabbit.publish({"listing_id": listing_id, "url": url})
        processed += 1

    driver.quit()
    rabbit.close()
    print(f"[PRODUCER] DONE — {processed} scraped, {errors} errors")


if __name__ == "__main__":
    main()