import pika
import json
from datetime import datetime
from bina.config import settings
from bina.db import DBClient
from bina.scraper import SeleniumDriver
from bina.models import Flat

def process_message(message: dict, db: DBClient, browser: SeleniumDriver):
    """Insert listing with full details into DB."""
    flat = Flat(
        listing_id=message["listing_id"],
        url=message["url"],
        title=message.get("title"),
        price_azn=message.get("price_azn"),
        price_per_sqm=message.get("price_per_sqm"),
        rooms=message.get("rooms"),
        area_sqm=message.get("area_sqm"),
        floor_current=message.get("floor_current"),
        floor_total=message.get("floor_total"),
        location_area=message.get("location_area"),
        location_city=message.get("location_city"),
        owner_type=message.get("owner_type"),
        has_mortgage=message.get("has_mortgage"),
        has_deed=message.get("has_deed"),
        posted_at=None if message.get("posted_at") is None else 
            datetime.fromisoformat(message["posted_at"]),
    )
    db.insert_new([flat])
    print(f"[x] Inserted listing {flat.listing_id}")


def main():
    db = DBClient()
    browser = SeleniumDriver()
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=settings.RABBIT_HOST,
            port=settings.RABBIT_PORT,
            credentials=pika.PlainCredentials(settings.RABBIT_USER, settings.RABBIT_PASSWORD),
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue=settings.RABBIT_QUEUE, durable=True)

    def callback(ch, method, properties, body):
        msg = json.loads(body)
        process_message(msg, db, browser)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)  # one message at a time
    channel.basic_consume(queue=settings.RABBIT_QUEUE, on_message_callback=callback)
    print("[*] Waiting for messages")
    channel.start_consuming()

if __name__ == "__main__":
    main()
