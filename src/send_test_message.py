import json
import pika

# Since we are running this script on the HOST, not inside Docker,
# we must connect to RabbitMQ via localhost.
RABBIT_HOST = "127.0.0.1"
RABBIT_PORT = 5672
RABBIT_USER = "aliyev.user"
RABBIT_PASSWORD = "EtlRabbitBlack1002025Xyz"
RABBIT_QUEUE = "listing_queue"

message = {
    "listing_id": 5129390,
    "url": "https://bina.az/items/5129390"
}

connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host=RABBIT_HOST,
        port=RABBIT_PORT,
        credentials=pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD)
    )
)

channel = connection.channel()
channel.queue_declare(queue=RABBIT_QUEUE, durable=True)

channel.basic_publish(
    exchange='',
    routing_key=RABBIT_QUEUE,
    body=json.dumps(message),
    properties=pika.BasicProperties(delivery_mode=2),
)

print("[x] Test message sent!")
connection.close()
