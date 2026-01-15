#!/usr/bin/env python3
import json, pika
from bina.config import settings

msg = {"listing_id": 5272466, "url": "https://bina.az/items/5272466"}

conn = pika.BlockingConnection(pika.ConnectionParameters(
    host=settings.RABBIT_HOST,
    port=settings.RABBIT_PORT,
    credentials=pika.PlainCredentials(settings.RABBIT_USER, settings.RABBIT_PASSWORD),
))
ch = conn.channel()
ch.queue_declare(queue=settings.RABBIT_QUEUE, durable=True)
ch.basic_publish(
    exchange='',
    routing_key=settings.RABBIT_QUEUE,
    body=json.dumps(msg),
    properties=pika.BasicProperties(delivery_mode=2),
)
print("[x] Test message sent to", settings.RABBIT_QUEUE)
conn.close()
