import json
import pika
from bina.config import settings
from bina.scraper import SeleniumDriver
from bina.pipeline import Pipeline
from bina.db import DBClient

def flat_to_dict(flat):
    """Convert Flat object to dictionary suitable for JSON."""
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

def main():
    db = DBClient()  # Connect to DB to check existing IDs

    # Connect to RabbitMQ
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=settings.RABBIT_HOST,
            port=settings.RABBIT_PORT,
            credentials=pika.PlainCredentials(settings.RABBIT_USER, settings.RABBIT_PASSWORD),
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue=settings.RABBIT_QUEUE, durable=True)

    # Start scraper
    browser = SeleniumDriver()
    pipe = Pipeline(db=None, browser=browser)  # DB is None, only sending messages

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

            # Check against DB for duplicates
            new_ids = [lid for lid, _, _ in new_cards]
            existing_ids = db.listing_ids_exist(new_ids)

            for lid, url, el in new_cards:
                if lid in existing_ids:
                    continue  # Skip already in DB

                flat = pipe.browser.parse_card(lid, url, el)
                flats.append(flat)

                # Send to RabbitMQ
                message = flat_to_dict(flat)
                channel.basic_publish(
                    exchange='',
                    routing_key=settings.RABBIT_QUEUE,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                    )
                )
                print(f"[x] Sent listing {flat.listing_id}")

            browser.scroll_once()

    finally:
        browser.close()
        connection.close()
        db.close()

if __name__ == "__main__":
    main()
