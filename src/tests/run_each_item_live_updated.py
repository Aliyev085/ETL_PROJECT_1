#!/usr/bin/env python3
# tests/run_each_item_live_updated.py

from bina.scraper_each_item import scrape_listing

if __name__ == "__main__":
    url = input("Enter full bina.az item URL: ").strip()
    if not url:
        raise SystemExit("❌ No URL provided.")
    try:
        listing_id = int(url.rstrip("/").split("/")[-1])
    except Exception:
        raise SystemExit("❌ Could not parse listing_id from URL.")

    scrape_listing({"listing_id": listing_id, "url": url})
