#!/usr/bin/env python3
# scraper_each_item.py

import json
import re
import time
import sys
import os
from concurrent.futures import ThreadPoolExecutor
import psycopg2

# ---------- ENVIRONMENT DEBUG ----------
print("\n[DEBUG] ENVIRONMENT CHECK:")
for key in ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD", "RABBIT_HOST", "RABBIT_QUEUE"]:
    print(f"  {key} = {os.getenv(key)}")
print("[DEBUG] Current working dir:", os.getcwd(), flush=True)
print("[DEBUG] Python executable:", sys.executable, flush=True)
print("[DEBUG] PID:", os.getpid(), flush=True)
print("-" * 60, flush=True)
# --------------------------------------

try:
    import undetected_chromedriver as uc  # stealth driver
    _USE_UC = True
except Exception:
    from selenium import webdriver
    _USE_UC = False

# ---------- stdout fix ----------
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bina.config import settings
from bina.rabbit import RabbitMQ

# ---------- Helpers ----------

def normalize_phone(number: str | None) -> str | None:
    if not number:
        return None
    n = re.sub(r"\D", "", number)
    if n.startswith("994"):
        n = n[3:]
    elif n.startswith("0"):
        n = n[1:]
    if not n:
        return None
    return "+994 " + n


def extract_view_count(text: str | None) -> int | None:
    if not text:
        return None
    m = re.search(r"(\d[\d\s]*)", text)
    if not m:
        return None
    return int(m.group(1).replace(" ", ""))


def safe_text(driver, by, selector, timeout=8):
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, selector))
        )
        return el.text.strip() or None
    except Exception:
        return None


# ---------- Database ----------

class DBClient:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            dbname=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
        )
        self.conn.autocommit = False

    def update_listing(self, listing_id: int, data: dict):
        if not data:
            return
        try:
            listing_id = int(listing_id)
        except Exception:
            print(f"[WARN] Invalid listing_id: {listing_id}", flush=True)
            return

        cols = ", ".join(f"{k}=%s" for k in data.keys())
        vals = list(data.values()) + [listing_id]
        q = f"UPDATE bina_apartments SET {cols} WHERE listing_id=%s"

        try:
            with self.conn.cursor() as c:
                c.execute(q, vals)
                print(f"[DB] Updated listing_id={listing_id} ({c.rowcount} rows)", flush=True)
            self.conn.commit()
        except Exception as e:
            print(f"[DB ERROR] Failed to update {listing_id}: {e}", flush=True)
            self.conn.rollback()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


# ---------- Selenium ----------

def create_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--lang=az-AZ")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    try:
        driver = uc.Chrome(options=opts, headless=True) if _USE_UC else webdriver.Chrome(options=opts)
    except Exception as e:
        print(f"[DRIVER ERROR] Failed to start Chrome: {e}", flush=True)
        raise

    driver.set_page_load_timeout(60)
    return driver


# ---------- Phone fetchers ----------

def fetch_phone_via_inpage_fetch(driver, listing_id: int) -> str | None:
    try:
        js = f"""
        const tokenEl = document.querySelector('meta[name="csrf-token"]');
        const token = tokenEl ? tokenEl.getAttribute('content') : '';
        return fetch('/items/{listing_id}/phones?trigger_button=main', {{
            method: 'GET',
            headers: {{
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRF-Token': token
            }},
            credentials: 'same-origin'
        }}).then(r => r.text()).then(txt => txt).catch(e => 'ERR:'+String(e));
        """
        resp_text = driver.execute_script(js)
        if isinstance(resp_text, str) and not resp_text.startswith("ERR:"):
            for pattern in [r"\+994\d{9}", r"\(?0\d{2}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}"]:
                m = re.search(pattern, resp_text)
                if m:
                    return normalize_phone(m.group(0))
    except Exception as e:
        print(f"[DEBUG] in-page fetch() failed: {e}", flush=True)
    return None


def fetch_phone_via_dom(driver) -> str | None:
    try:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, ".product-phones__btn, [data-cy='show-phone']")
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(1.2)
        except Exception:
            pass

        for css in [
            "//a[starts-with(@href,'tel:')]",
            ".product-phones__btn-value",
            ".js-phones",
        ]:
            try:
                el = driver.find_element(By.XPATH if css.startswith("//") else By.CSS_SELECTOR, css)
                txt = el.text.strip()
                if txt and "●" not in txt:
                    return normalize_phone(txt)
            except Exception:
                continue
    except Exception as e:
        print(f"[DEBUG] DOM phone fallback failed: {e}", flush=True)
    return None


# ---------- Core ----------

def scrape_listing(detail: dict):
    lid, url = detail.get("listing_id"), detail.get("url")
    print(f"\n[SCRAPE] Starting listing {lid} → {url}", flush=True)

    driver = create_driver()
    db = DBClient()

    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(1.0)

        desc = safe_text(driver, By.CSS_SELECTOR, ".product-description__content p")
        owner = safe_text(driver, By.CSS_SELECTOR, ".product-owner__info-name")

        phone = fetch_phone_via_inpage_fetch(driver, lid) or fetch_phone_via_dom(driver)
        views_txt = (
            safe_text(driver, By.CSS_SELECTOR, "[data-cy='statistics-views']")
            or safe_text(driver, By.XPATH, "//span[contains(text(),'Baxış')]")
        )
        views = extract_view_count(views_txt)

        try:
            driver.find_element(By.CSS_SELECTOR, ".product-labels__i-icon--repair")
            is_constructed = True
        except Exception:
            is_constructed = False

        print(f"[SCRAPE] ID={lid}, Owner={owner}, Phone={phone}, Views={views}, Constructed={is_constructed}", flush=True)

        payload = {"is_scraped": True}
        if desc: payload["description"] = desc
        if owner: payload["posted_by"] = owner
        if phone: payload["contact_number"] = phone
        if views is not None: payload["view_count"] = views
        payload["is_constructed"] = is_constructed

        db.update_listing(lid, payload)
        print(f"[SCRAPE] ✅ Listing {lid} updated successfully", flush=True)

    except Exception as e:
        print(f"[!] Error scraping listing {lid}: {e}", flush=True)
    finally:
        driver.quit()
        db.close()


# ---------- RabbitMQ ----------

def main():
    rabbit = RabbitMQ()
    execs = ThreadPoolExecutor(max_workers=3)

    def callback(ch, method, props, body):
        try:
            print("\n[CALLBACK] Triggered!", flush=True)
            d = json.loads(body)
            print(f"[CALLBACK] Received message: {d}", flush=True)
            execs.submit(scrape_listing, d)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print("[CALLBACK] Ack sent ✅", flush=True)
        except Exception as e:
            print(f"[CALLBACK ERROR] {e}", file=sys.stderr, flush=True)

    rabbit.channel.basic_qos(prefetch_count=3)
    rabbit.channel.basic_consume(queue=settings.RABBIT_QUEUE, on_message_callback=callback)
    print("[*] Waiting for messages...", flush=True)

    try:
        rabbit.channel.start_consuming()
    except KeyboardInterrupt:
        print("\n[!] Exiting gracefully...", flush=True)
    finally:
        rabbit.close()
        execs.shutdown(wait=True)
        print("[!] Shutdown complete.", flush=True)


if __name__ == "__main__":
    main()
