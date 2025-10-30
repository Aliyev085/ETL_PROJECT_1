#!/usr/bin/env python3
# tests/run_each_item_local_html.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time, os

def main():
    html_path = os.path.abspath("Untitled-1.txt")  # adjust if file is elsewhere
    print(f"[TEST] Loading local file: {html_path}")

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=opts)

    try:
        driver.get("file://" + html_path)
        time.sleep(1)

        # ---- description ----
        try:
            desc = driver.find_element(By.CSS_SELECTOR, ".product-description__content p").text
        except Exception:
            desc = None

        # ---- owner ----
        try:
            owner = driver.find_element(By.CSS_SELECTOR, ".product-owner__info-name").text
        except Exception:
            owner = None

        # ---- contact ----
        try:
            contact = driver.find_element(By.CSS_SELECTOR, ".product-phones__btn-value").text
        except Exception:
            contact = None

        # ---- view count ----
        try:
            views = driver.find_element(By.XPATH, "//span[contains(text(), 'Baxışların sayı')]").text
        except Exception:
            views = None

        print("\n[RESULTS]")
        print(f"Description : {desc}")
        print(f"Owner       : {owner}")
        print(f"Contact     : {contact}")
        print(f"Views       : {views}")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
