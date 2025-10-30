#!/usr/bin/env python3
# src/tests/run_each_item_live.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

def main():
    url = input("Enter full bina.az item URL: ").strip()

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=opts)

    try:
        driver.get(url)
        time.sleep(3)  # wait for page load

        def safe_find(selector, by=By.CSS_SELECTOR):
            try:
                return driver.find_element(by, selector).text.strip()
            except Exception:
                return None

        desc = safe_find(".product-description__content p")
        owner = safe_find(".product-owner__info-name")
        contact = safe_find(".product-phones__btn-value")
        views = safe_find("//span[contains(text(),'Baxış')]", by=By.XPATH)

        print("\n[RESULTS]")
        print(f"Description : {desc}")
        print(f"Owner       : {owner}")
        print(f"Contact     : {contact}")
        print(f"Views       : {views}")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
