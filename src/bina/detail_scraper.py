#!/usr/bin/env python3
# FULLY FIXED DETAIL SCRAPER FOR BINA.AZ (2025)
# ----------------------------------------------
# Based on ACTUAL HTML selectors provided
# ----------------------------------------------

from __future__ import annotations
import time
import re

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bina.config import settings
from bina.db import upsert_listing_detail, is_listing_scraped
from bina.rabbit import RabbitMQ


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
# FIELD EXTRACTORS - FIXED BASED ON ACTUAL HTML
# ----------------------------------------------------------

def extract_description(driver):
    """
    Description container:
    <div id="read-more" data-cy="read-more" class="sc-639be663-0 dujDNV">...</div>
    OR
    <div class="product-description__content">...</div>
    """
    selectors = [
        "#read-more",
        "[data-cy='read-more']",
        ".product-description__content",
        "[class*='product-description']",
    ]
    
    for sel in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            txt = el.text.strip()
            if txt and len(txt) > 10:
                print(f"[DETAIL] Description found ({len(txt)} chars) via {sel}")
                return txt
        except:
            pass
    
    print("[DETAIL] Description NOT FOUND")
    return None


def extract_posted_by(driver):
    """
    Owner name:
    NEW: <span class="sc-3381e952-0 iNKNZX sc-4d25592c-2 GmovA">Cabrayıl</span>
    OLD: <div class="product-owner__info-name">Name</div>
    """
    selectors = [
        # New format - class contains sc-4d25592c-2
        "[class*='sc-4d25592c-2']",
        ".GmovA",
        # Old format
        ".product-owner__info-name",
        "[class*='product-owner']",
        # Generic fallback - look in owner section
        "[class*='owner'] span",
    ]
    
    for sel in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            txt = el.text.strip()
            # Validate: should be a name (1-50 chars, not a number)
            if txt and len(txt) < 50 and not txt.isdigit():
                print(f"[DETAIL] Posted by: '{txt}' via {sel}")
                return txt
        except:
            pass
    
    print("[DETAIL] Posted by NOT FOUND")
    return None


def extract_phone(driver):
    """
    Phone reveal button (OLD style):
    <div class="js-show-phones product-phones__btn">
    
    After click, phone appears (NEW style):
    <a href="tel:+994502898777" class="sc-b43c2f10-5 eMlMfC">+994 50 289 87 77</a>
    
    OR (OLD style):
    <div class="js-phones"><a href="tel:...">...</a></div>
    """
    phone = None
    
    # Try to find and click the reveal button
    btn_selectors = [
        ".js-show-phones",
        "#show-phones",
        "[class*='product-phones__btn']",
        "button[class*='phone']",
        "[data-cy*='phone']",
    ]
    
    clicked = False
    for sel in btn_selectors:
        try:
            btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
            )
            driver.execute_script("arguments[0].click();", btn)
            print(f"[DETAIL] Clicked phone button via {sel}")
            clicked = True
            time.sleep(2)
            break
        except:
            pass
    
    if not clicked:
        print("[DETAIL] Could not click phone button")
    
    # Now try to find the revealed phone number
    phone_selectors = [
        # New format
        "a[href^='tel:'][class*='sc-b43c2f10']",
        "a[href^='tel:'][class*='eMlMfC']",
        # Old format
        ".js-phones a[href^='tel:']",
        # Generic
        "a[href^='tel:']",
    ]
    
    for sel in phone_selectors:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                href = el.get_attribute("href")
                if href and href.startswith("tel:"):
                    phone = href.replace("tel:", "").strip()
                    # Clean the phone
                    phone = re.sub(r"[^\d+]", "", phone)
                    if len(phone) >= 9:
                        print(f"[DETAIL] Phone: {phone} via {sel}")
                        return phone
        except:
            pass
    
    # Fallback: search for phone pattern in page
    try:
        html = driver.page_source
        # Match Azerbaijan phone: +994 XX XXX XX XX
        m = re.search(r"\+994\s*\d{2}\s*\d{3}\s*\d{2}\s*\d{2}", html)
        if m:
            phone = re.sub(r"[^\d+]", "", m.group(0))
            print(f"[DETAIL] Phone (fallback): {phone}")
            return phone
    except:
        pass
    
    print("[DETAIL] Phone NOT FOUND")
    return None


def extract_view_count(driver):
    """
    View count:
    <span class="product-statistics__i-text">Baxışların sayı: 760</span>
    """
    selectors = [
        ".product-statistics__i-text",
        "[class*='product-statistics'] span",
        "[class*='statistics'] span",
    ]
    
    for sel in selectors:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                txt = el.text
                if "Baxış" in txt or "baxış" in txt:
                    m = re.search(r"(\d+)", txt)
                    if m:
                        count = int(m.group(1))
                        print(f"[DETAIL] View count: {count}")
                        return count
        except:
            pass
    
    # Fallback: search in page source
    try:
        html = driver.page_source
        m = re.search(r"Baxışların\s+sayı[:\s]+(\d+)", html, re.IGNORECASE)
        if m:
            count = int(m.group(1))
            print(f"[DETAIL] View count (fallback): {count}")
            return count
    except:
        pass
    
    print("[DETAIL] View count NOT FOUND")
    return None


def extract_is_constructed(driver):
    """
    Repair/construction badge:
    <div class="product-labels__i-icon product-labels__i-icon--repair"></div>Təmirli
    """
    # Check for repair badge icon
    badge_selectors = [
        ".product-labels__i-icon--repair",
        "[class*='product-labels__i-icon--repair']",
        "[class*='icon--repair']",
    ]
    
    for sel in badge_selectors:
        try:
            driver.find_element(By.CSS_SELECTOR, sel)
            print("[DETAIL] Is constructed: True (badge found)")
            return True
        except:
            pass
    
    # Fallback: check for keywords in page
    try:
        html = driver.page_source.lower()
        keywords = ["təmirli", "tam təmir", "yeni təmir", "təmir olunub"]
        for kw in keywords:
            if kw in html:
                print(f"[DETAIL] Is constructed: True (keyword '{kw}')")
                return True
    except:
        pass
    
    print("[DETAIL] Is constructed: False")
    return False


# ----------------------------------------------------------
# MAIN LOOP
# ----------------------------------------------------------
def main(max_items=settings.DETAIL_SCRAPER_LIMIT, max_seconds=300):
    print("[DETAIL] START")
    
    rabbit = RabbitMQ()
    driver = get_driver()

    processed = 0
    errors = 0
    start = time.time()

    while True:

        msg = rabbit.consume_one(settings.RABBIT_QUEUE)
        if not msg:
            print("[DETAIL] Queue empty — stopping")
            break

        listing_id = msg.get("listing_id")
        url = msg.get("url")

        if not listing_id or not url:
            print(f"[DETAIL] Invalid message: {msg}")
            continue

        print(f"\n[DETAIL] ===== Processing {listing_id} =====")
        print(f"[DETAIL] URL: {url}")

        try:
            # CHECK DATABASE FIRST
            if is_listing_scraped(listing_id):
                print(f"[DETAIL] ⏭️  SKIPPED — {listing_id} already scraped")
                # Notify RabbitMQ that task is complete (skipped)
                rabbit.publish_completion(
                    listing_id=listing_id,
                    status="skipped",
                    message="Already scraped (is_scraped=True)"
                )
                processed += 1
                continue

            # Proceed with scraping
            driver.get(url)
            time.sleep(3)  # Wait for page load

            description = extract_description(driver)
            posted_by = extract_posted_by(driver)
            phone = extract_phone(driver)
            views = extract_view_count(driver)
            is_const = extract_is_constructed(driver)

            # Summary
            print(f"[DETAIL] --- SUMMARY ---")
            print(f"[DETAIL] description: {'✓' if description else '✗'} ({len(description) if description else 0} chars)")
            print(f"[DETAIL] posted_by: {posted_by or '✗'}")
            print(f"[DETAIL] phone: {phone or '✗'}")
            print(f"[DETAIL] views: {views or '✗'}")
            print(f"[DETAIL] is_constructed: {is_const}")

            upsert_listing_detail(
                listing_id=listing_id,
                description=description,
                posted_by=posted_by,
                contact_number=phone,
                view_count=views,
                is_constructed=is_const,
                is_scraped=True,
            )

            processed += 1
            print(f"[DETAIL] ✓ SAVED {listing_id}")
            
            # Notify RabbitMQ that task completed successfully
            rabbit.publish_completion(
                listing_id=listing_id,
                status="success",
                message="Successfully scraped and saved"
            )

        except Exception as e:
            errors += 1
            print(f"[DETAIL] ✗ ERROR {listing_id}: {e}")
            import traceback
            traceback.print_exc()
            
            # Notify RabbitMQ about the error
            rabbit.publish_completion(
                listing_id=listing_id,
                status="error",
                message=str(e)
            )

    driver.quit()
    rabbit.close()
    print(f"\n[DETAIL] DONE — {processed} scraped, {errors} errors")


if __name__ == "__main__":
    main()