import json
import pika
from src.bina.config import settings

# Example data for one listing
message = {
    "listing_id": 123,  # replace with a real listing ID from your DB
    "url": "https://example.com/listing/123"  # replace with a real URL to scrape
}

connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host=settings.RABBIT_HOST,
        port=settings.RABBIT_PORT,
        credentials=pika.PlainCredentials(settings.RABBIT_USER, settings.RABBIT_PASSWORD)
    )
)
channel = connection.channel()
channel.queue_declare(queue=settings.RABBIT_QUEUE, durable=True)

channel.basic_publish(
    exchange='',
    routing_key=settings.RABBIT_QUEUE,
    body=json.dumps(message),
    properties=pika.BasicProperties(
        delivery_mode=2,  # make message persistent
    )
)

print("[x] Test message sent!")
connection.close()
