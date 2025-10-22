import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost', port=5672, credentials=pika.PlainCredentials('aliyev.user', 'AliyevServerBlack1002025Xyz'))
)
channel = connection.channel()
channel.queue_declare(queue='test_queue')

def callback(ch, method, properties, body):
    print(f"[x] Received: {body.decode()}")
    # Acknowledge the message
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(queue='test_queue', on_message_callback=callback, auto_ack=False)

print('[*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()
