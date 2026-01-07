import json
import logging
import os
import time
import pika
from typing import Dict, Any

from netra_backend.logging_config import setup_logging
from netra_backend.db_client import PostgresClient

logger = logging.getLogger("db_worker")

class DBWorkerService:
    def __init__(self):
        # 1. Initialize the existing DB client (maintains same table structure)
        self.db = PostgresClient()

        # 2. RabbitMQ Config
        self.rabbitmq_url = os.getenv(
            "RABBITMQ_URL",
            "amqp://Netra:netra%40123@127.0.0.1:5673/%2f?heartbeat=0",
        )
        self.exchange = os.getenv("RABBITMQ_OUTPUT_EXCHANGE", "telemetry.decoded")
        self.queue_name = "q.decoded.db_persistence"

    def run_forever(self) -> None:
        while True:
            try:
                self._consume_once()
            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt: stopping db worker")
                break
            except Exception as e:
                logger.exception("Top-level error in DBWorkerService: %s. Reconnecting in 5s", e)
                time.sleep(5.0)

    def _consume_once(self) -> None:
        logger.info("Connecting to RabbitMQ for DB worker: %s", self.rabbitmq_url)
        params = pika.URLParameters(self.rabbitmq_url)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()

        # 1. Declare the exchange (idempotent, ensures it exists)
        channel.exchange_declare(
            exchange=self.exchange, 
            exchange_type='topic', 
            durable=True
        )

        # 2. Declare the durable queue for DB persistence
        channel.queue_declare(queue=self.queue_name, durable=True)

        # 3. Bind queue to exchange to receive EVERYTHING ('#')
        channel.queue_bind(
            exchange=self.exchange,
            queue=self.queue_name,
            routing_key='#'
        )
        logger.info("Bound queue %s to exchange %s with key '#'", self.queue_name, self.exchange)

        # 4. Start consuming
        channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=self._on_message,
        )

        logger.info("Starting DB Worker consuming loop...")
        try:
            channel.start_consuming()
        finally:
            if connection and connection.is_open:
                connection.close()

    def _on_message(self, ch, method, properties, body):
        """
        Payload structure from health_consumer:
        {
          "meta": { "packet_name": "...", ... },
          "data": [ {row_dict}, ... ]
        }
        """
        try:
            msg = json.loads(body.decode("utf-8"))
        except Exception as e:
            logger.error("Failed to parse JSON: %s", e)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        meta = msg.get("meta", {})
        rows = msg.get("data", [])
        
        packet_name = meta.get("packet_name", "UNKNOWN_PACKET")

        if not rows:
            logger.warning("Received message for %s with no data rows", packet_name)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        try:
            target_table = packet_name
            if "__" in target_table:
                parts = target_table.split("__")
                if len(parts) >= 4 and parts[2] == "EMULATOR":
                     target_table = "__".join(parts[3:])
            
            self.db.ensure_table_for_packet(target_table, rows[0])
            self.db.insert_rows(target_table, rows)
            
            logger.info("Inserted %d rows into %s", len(rows), target_table)

        except Exception as e:
            logger.exception("DB Error inserting for %s", packet_name)
            self.db.insert_decoder_failed(packet_name, "JSON_PAYLOAD", f"db_worker_error: {e}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    setup_logging()
    svc = DBWorkerService()
    svc.run_forever()

if __name__ == "__main__":
    main()
