#!/usr/bin/env python3
# test_rabbit_second.py

import json
from bina.rabbit import RabbitMQ
from bina.config import settings

def main():
    rabbit = RabbitMQ()
    try:
        message = {
            "listing_id": 999,  # change to a valid ID from your DB
            "url": "https://example.com"  # change to a real listing URL
        }
        rabbit.publish(message)
        print("Message sent!")
    finally:
        rabbit.close()

if __name__ == "__main__":
    main()
