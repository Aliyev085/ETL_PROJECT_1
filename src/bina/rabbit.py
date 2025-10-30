from __future__ import annotations
import pika
import json
from .config import settings

class RabbitMQ:
    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBIT_HOST,
                port=settings.RABBIT_PORT,
                credentials=pika.PlainCredentials(
                    settings.RABBIT_USER, settings.RABBIT_PASSWORD
                ),
            )
        )
        self.channel = self.connection.channel()
        # Declare the queue
        self.channel.queue_declare(queue=settings.RABBIT_QUEUE, durable=True)

    def publish(self, message: dict):
        """Send a JSON message to the queue."""
        self.channel.basic_publish(
            exchange='',
            routing_key=settings.RABBIT_QUEUE,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            )
        )

    def close(self):
        self.connection.close()
