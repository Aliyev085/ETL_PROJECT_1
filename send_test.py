import pika

# Connection parameters
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost', port=5672, credentials=pika.PlainCredentials('aliyev.user', 'AliyevServerBlack1002025Xyz'))
)
channel = connection.channel()

# Declare a queue (it must exist on both sides)
channel.queue_declare(queue='test_queue')

# Send a message
channel.basic_publish(exchange='', routing_key='test_queue', body='Hello ETL!')

print("[x] Sent 'Hello ETL!'")
connection.close()
