import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host='127.0.0.1',  # or the RabbitMQ container IP
        port=5672,
        credentials=pika.PlainCredentials('aliyev.user', 'EtlServerBlack1002025Xyz')
    )
)
channel = connection.channel()
channel.queue_declare(queue='listing_queue', durable=True)
channel.basic_publish(
    exchange='',
    routing_key='listing_queue',
    body='{"listing_id":123,"url":"https://example.com"}'
)
print("Message sent!")
connection.close()
