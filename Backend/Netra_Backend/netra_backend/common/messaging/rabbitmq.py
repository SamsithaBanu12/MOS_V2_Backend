# netra_backend/common/messaging/rabbitmq.py
import json
import logging
import os
import time
from typing import Dict, List, Optional

import pika

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    """
    Simple, reconnecting RabbitMQ publisher.

    - Uses RABBITMQ_URL env var (amqp://user:pass@host:port/vhost)
    - Publishes to a direct exchange (default: telemetry.raw)
    - Can also create one queue per packet and bind them.
    """

    def __init__(self, exchange: str = "telemetry.raw"):
        self.exchange = os.getenv("RABBITMQ_EXCHANGE", exchange)
        # NOTE: password has '@', so in URL it must be encoded as '%40'
        self.url = os.getenv(
            "RABBITMQ_URL",
            "amqp://Netra:netra%40123@127.0.0.1:5673/%2f",
        )
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None

        logger.info("RabbitMQPublisher using url=%s exchange=%s", self.url, self.exchange)
        self._ensure_connection()

    def _ensure_connection(self) -> None:
        """
        Ensure connection & channel exist. Reconnect if needed.
        This should not raise to caller; we log errors instead.
        """
        if self._connection and self._connection.is_open and self._channel and self._channel.is_open:
            return

        for attempt in range(1, 4):
            try:
                params = pika.URLParameters(self.url)
                self._connection = pika.BlockingConnection(params)
                self._channel = self._connection.channel()
                # Declare direct exchange (idempotent)
                self._channel.exchange_declare(
                    exchange=self.exchange,
                    exchange_type="direct",
                    durable=True,
                )
                logger.info("Connected to RabbitMQ on attempt %d", attempt)
                return
            except Exception as e:
                logger.exception("Error connecting to RabbitMQ (attempt %d): %s", attempt, e)
                time.sleep(2.0)

        logger.error("Failed to connect to RabbitMQ after several attempts. Will retry on next publish.")

    def setup_queues_for_packets(self, packet_names: List[str]) -> None:
        """
        For each packet name, create a dedicated queue and bind it.

        Queue name: pkt.<packet_name>
        Binding:    exchange=self.exchange, routing_key=<packet_name>
        """
        self._ensure_connection()
        if not self._channel or not self._channel.is_open:
            logger.error("Cannot setup queues: RabbitMQ channel not available")
            return

        for pkt_name in packet_names:
            queue_name = f"pkt.{pkt_name}"
            try:
                self._channel.queue_declare(queue=queue_name, durable=True)
                self._channel.queue_bind(
                    exchange=self.exchange,
                    queue=queue_name,
                    routing_key=pkt_name,
                )
                logger.info("Declared queue %s bound to %s with RK=%s",
                            queue_name, self.exchange, pkt_name)
            except Exception:
                logger.exception("Error declaring/binding queue for packet %s", pkt_name)

    def publish_json(self, routing_key: str, message: Dict) -> None:
        """
        Publish a JSON-serializable dict to the exchange with the given routing key.
        """
        body = json.dumps(message, default=str).encode("utf-8")

        try:
            self._ensure_connection()
            if not self._channel or not self._channel.is_open:
                logger.error("RabbitMQ channel not available; dropping message with RK=%s", routing_key)
                return

            self._channel.basic_publish(
                exchange=self.exchange,
                routing_key=routing_key,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                ),
            )
            logger.debug("Published message to %s", routing_key)
        except Exception:
            logger.exception("Error publishing message to RabbitMQ (RK=%s)", routing_key)
