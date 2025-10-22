from __future__ import annotations
from typing import List

from .db import DBClient
from .scraper import SeleniumDriver
from .models import Flat
from .rabbit import RabbitMQ


class Pipeline:
    """Scraper pipeline: can insert new listings into DB or publish links to RabbitMQ."""

    def __init__(self, db: DBClient, browser: SeleniumDriver) -> None:
        self.db = db
        self.browser = browser

    def verify(self) -> bool:
        """Check if cards are visible on the main page."""
        cards = self.browser.collect_cards()
        return bool(cards)

    # --------------------------
    # Old behavior: scrape and insert
    # --------------------------
    def run(self, max_new: int = 100) -> int:
        """Scroll, collect cards, parse details, and insert only new rows into DB."""
        seen: set[int] = set()
        flats: List[Flat] = []
        inserted_total = 0

        while len(flats) < max_new:
            cards = self.browser.collect_cards()
            if not cards:
                break

            new_cards = [(lid, url, el) for lid, url, el in cards if lid not in seen]
            if not new_cards:
                break

            seen.update([lid for lid, _, _ in new_cards])
            for lid, url, el in new_cards:
                # 🔍 Print outerHTML of the first card for debugging
                if not flats:
                    sample_html = el.find_element("xpath", "..").get_attribute("outerHTML")
                    print("\n[DEBUG] Sample card HTML:\n", sample_html)

                flat = self.browser.parse_card(lid, url, el)
                flats.append(flat)
                if len(flats) >= max_new:
                    break

            self.browser.scroll_once()

        if not flats:
            return 0

        # Filter out IDs that already exist in DB
        existing = self.db.listing_ids_exist([f.listing_id for f in flats])
        new_flats = [f for f in flats if f.listing_id not in existing]

        if not new_flats:
            return 0

        # 🔍 DEBUG: print a preview of each Flat before inserting
        print("\n[DEBUG] New flats about to be inserted:")
        for flat in new_flats:
            print(
                f"ID={flat.listing_id}, Title={flat.title}, Price={flat.price_azn}, "
                f"Rooms={flat.rooms}, Area={flat.area_sqm}, Location={flat.location_area}/{flat.location_city}"
            )

        inserted = self.db.insert_new(new_flats)
        inserted_total += inserted
        return inserted_total

    # --------------------------
    # New behavior: producer for RabbitMQ
    # --------------------------
    def run_producer(self, max_new: int = 100) -> int:
        """Collect new cards and publish only listing IDs + URLs to RabbitMQ."""
        seen: set[int] = set()
        published = 0
        rabbit = RabbitMQ()
        try:
            while published < max_new:
                cards = self.browser.collect_cards()
                if not cards:
                    break

                new_cards = [(lid, url) for lid, url, _ in cards if lid not in seen]
                if not new_cards:
                    break

                for lid, url in new_cards:
                    rabbit.publish({"listing_id": lid, "url": url})
                    published += 1
                    seen.add(lid)
                    if published >= max_new:
                        break

                self.browser.scroll_once()
        finally:
            rabbit.close()

        return published
