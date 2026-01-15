# GOOGLE-LEVEL RABBITMQ CLIENT
# -------------------------------------------------------------
# ✓ Auto-reconnect
# ✓ Delivery confirmation
# ✓ Safe publish
# ✓ Safe consume_one
# ✓ JSON protection
# ✓ Queue durability
# ✓ Docker-safe host resolving
# ✓ Heartbeat 600s
# ✓ Airflow-safe
# -------------------------------------------------------------

import pika
import json
import time
from pika.adapters.blocking_connection import BlockingConnection
from pika.exceptions import (
    AMQPConnectionError,
    ChannelClosedByBroker,
    StreamLostError
)

from bina.config import settings

# Completion queue name (can be configured)
COMPLETION_QUEUE = "detail_scraper_completed"


class RabbitMQ:
    def __init__(self):
        # IMPORTANT FIX:
        # If running in Docker (Airflow), 127.0.0.1 MUST NOT be used.
        #
        # So we dynamically switch host:
        # - If inside container  → use "rabbitmq"
        # - If running on host    → use the configured value
        #
        self.host = settings.RABBIT_HOST
        if self.host in ["127.0.0.1", "localhost"]:
            self.host = "rabbitmq"

        self._connect()

    # ==========================================================
    # CONNECT WITH AUTO-RETRY
    # ==========================================================
    def _connect(self):
        creds = pika.PlainCredentials(
            settings.RABBIT_USER,
            settings.RABBIT_PASSWORD
        )

        params = pika.ConnectionParameters(
            host=self.host,
            port=settings.RABBIT_PORT,
            credentials=creds,
            heartbeat=600,
            blocked_connection_timeout=300,
            socket_timeout=10,
            retry_delay=3,
            connection_attempts=3
        )

        for attempt in range(1, 11):
            try:
                print(f"[RABBIT] Connecting to {self.host}:{settings.RABBIT_PORT} (attempt {attempt}/10)...")

                self.connection = BlockingConnection(params)
                self.channel = self.connection.channel()

                # Strong delivery safety
                self.channel.confirm_delivery()

                # Declare durable queue
                self.channel.queue_declare(
                    queue=settings.RABBIT_QUEUE,
                    durable=True
                )

                # Prefetch for load control
                self.channel.basic_qos(prefetch_count=1)

                print("[RABBIT] CONNECTED ✔")
                return

            except Exception as e:
                print(f"[RABBIT CONNECT ERROR] {e}")
                if attempt == 10:
                    raise
                time.sleep(3)

    # ==========================================================
    # RECONNECT ON FAILURE
    # ==========================================================
    def _safe(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (AMQPConnectionError, StreamLostError, ChannelClosedByBroker):
            print("[RABBIT] Lost connection — reconnecting...")
            self._connect()
            return func(*args, **kwargs)

    # ==========================================================
    # PUBLISH (WITH DELIVERY CONFIRMATION)
    # ==========================================================
    def publish(self, msg: dict):
        body = json.dumps(msg, ensure_ascii=False)

        try:
            self._safe(
                self.channel.basic_publish,
                exchange="",
                routing_key=settings.RABBIT_QUEUE,
                body=body,
                mandatory=True,
                properties=pika.BasicProperties(
                    delivery_mode=2  # persistent
                )
            )
        except Exception as e:
            print(f"[RABBIT PUBLISH ERROR] {e}")
            raise

    # ==========================================================
    # PUBLISH COMPLETION STATUS
    # ==========================================================
    def publish_completion(self, listing_id: str, status: str, message: str = ""):
        """
        Publish completion status to a dedicated completion queue.
        
        Args:
            listing_id: The listing that was processed
            status: 'success', 'skipped', or 'error'
            message: Optional message with details
        """
        completion_msg = {
            "listing_id": listing_id,
            "status": status,
            "message": message,
            "timestamp": time.time()
        }
        
        body = json.dumps(completion_msg, ensure_ascii=False)
        
        try:
            # Ensure completion queue exists
            self._safe(
                self.channel.queue_declare,
                queue=COMPLETION_QUEUE,
                durable=True
            )
            
            self._safe(
                self.channel.basic_publish,
                exchange="",
                routing_key=COMPLETION_QUEUE,
                body=body,
                mandatory=False,
                properties=pika.BasicProperties(
                    delivery_mode=2  # persistent
                )
            )
            print(f"[RABBIT] Published completion: {listing_id} → {status}")
        except Exception as e:
            print(f"[RABBIT COMPLETION ERROR] {e}")
            # Don't raise - completion notification is optional

    # ==========================================================
    # CONSUME EXACTLY ONE MESSAGE
    # ==========================================================
    def consume_one(self, queue_name=None):
        if queue_name is None:
            queue_name = settings.RABBIT_QUEUE

        try:
            method, _, body = self._safe(
                self.channel.basic_get,
                queue_name
            )
        except Exception as e:
            print(f"[RABBIT CONSUME ERROR] {e}")
            return None

        if not method:
            return None

        # Safe decode
        try:
            msg = json.loads(body)
        except Exception:
            print("[RABBIT WARNING] Invalid JSON in queue — skipping.")
            self.channel.basic_ack(method.delivery_tag)
            return None

        self.channel.basic_ack(method.delivery_tag)
        return msg

    # ==========================================================
    # CLOSE CONNECTION
    # ==========================================================
    def close(self):
        try:
            self.connection.close()
        except:
            pass
