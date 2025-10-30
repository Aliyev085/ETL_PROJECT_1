# src/bina/producer.py

import json
import pika
import psycopg2
from bina.config import settings
from bina.scraper import SeleniumDriver
from bina.pipeline import Pipeline
from bina.db import DBClient


def flat_to_dict(flat):
    """Convert Flat object to dictionary suitable for JSON and DB upsert."""
    return {
        "listing_id": flat.listing_id,
        "url": flat.url,
        "title": flat.title,
        "price_azn": flat.price_azn,
        "price_per_sqm": flat.price_per_sqm,
        "rooms": flat.rooms,
        "area_sqm": flat.area_sqm,
        "floor_current": flat.floor_current,
        "floor_total": flat.floor_total,
        "location_area": flat.location_area,
        "location_city": flat.location_city,
        "owner_type": flat.owner_type,
        "has_mortgage": flat.has_mortgage,
        "has_deed": flat.has_deed,
        "posted_at": flat.posted_at.isoformat() if flat.posted_at else None,
    }


def upsert_card_into_db(flat):
    """Insert or update card-level data into bina_apartments table."""
    conn = None
    data = flat_to_dict(flat)

    # Remove listing_id to avoid duplicate column error
    data.pop("listing_id", None)
    data["is_scraped"] = False  # detail scraper not yet run

    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            dbname=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
        )
        conn.autocommit = False

        cols = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        update_clause = ", ".join([f"{c}=EXCLUDED.{c}" for c in data.keys()])

        q = f"""
        INSERT INTO bina_apartments (listing_id, {cols})
        VALUES (%s, {placeholders})
        ON CONFLICT (listing_id) DO UPDATE
        SET {update_clause};
        """

        vals = [flat.listing_id] + list(data.values())

        with conn.cursor() as cur:
            cur.execute(q, vals)

        conn.commit()
        print(f"[DB] UPSERT (card) listing_id={flat.listing_id} ✅", flush=True)

    except Exception as e:
        print(f"[DB ERROR] card upsert failed for {flat.listing_id}: {e}", flush=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def main():
    """Main producer that scrapes listing cards and pushes to RabbitMQ."""
    db = DBClient()

    # --- Setup RabbitMQ ---
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=settings.RABBIT_HOST,
            port=settings.RABBIT_PORT,
            credentials=pika.PlainCredentials(
                settings.RABBIT_USER, settings.RABBIT_PASSWORD
            ),
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue=settings.RABBIT_QUEUE, durable=True)

    # --- Setup Selenium Browser ---
    browser = SeleniumDriver()
    pipe = Pipeline(db=None, browser=browser)

    try:
        browser.get(settings.BINA_BASE_URL)
        max_new = settings.MAX_LISTINGS_INITIAL
        seen = set()
        flats = []

        while len(flats) < max_new:
            cards = browser.collect_cards()
            if not cards:
                break

            new_cards = [(lid, url, el) for lid, url, el in cards if lid not in seen]
            if not new_cards:
                break

            seen.update([lid for lid, _, _ in new_cards])
            new_ids = [lid for lid, _, _ in new_cards]
            existing_ids = db.listing_ids_exist(new_ids)

            for lid, url, el in new_cards:
                if lid in existing_ids:
                    continue

                # Parse summary info (card)
                flat = pipe.browser.parse_card(lid, url, el)
                flats.append(flat)

                # 1) Upsert card info into DB
                upsert_card_into_db(flat)

                # 2) Send to RabbitMQ for detail scraper
                message = flat_to_dict(flat)
                channel.basic_publish(
                    exchange="",
                    routing_key=settings.RABBIT_QUEUE,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(delivery_mode=2),
                )
                print(f"[x] Sent listing {flat.listing_id}")

            # Scroll to next batch
            browser.scroll_once()

    finally:
        browser.close()
        connection.close()
        db.close()


if __name__ == "__main__":
    main()
