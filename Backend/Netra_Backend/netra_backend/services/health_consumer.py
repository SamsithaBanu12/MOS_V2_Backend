# netra_backend/services/health_consumer.py
import base64
import importlib
import json
import logging
import time
import datetime
from typing import Any, Dict, List
import pika
import os

from netra_backend.logging_config import setup_logging
from netra_backend.config import get_openc3_config
from netra_backend.config import get_openc3_config
# DB Client removed to decouple service
# from netra_backend.db_client import PostgresClient

logger = logging.getLogger("health_consumer")


class DecoderNotFound(Exception):
    pass


def _get_health_packet_names() -> List[str]:
    """
    From OpenC3 config, pick only packets whose names contain '__HEALTH_'.
    These are considered 'health' packets.
    """
    cfg = get_openc3_config()
    all_packets = cfg.packets_tlm + cfg.packets_cmd
    health_packets = [p for p in all_packets if "__HEALTH_" in p]
    logger.info("Identified %d health packet types", len(health_packets))
    return health_packets


def _decode_buffer_to_hex(buffer_b64: str) -> str:
    """
    Convert OpenC3 'buffer' field (base64 with possible newlines) to a hex string.
    """
    clean_b64 = buffer_b64.replace("\n", "")
    raw_bytes = base64.b64decode(clean_b64)
    return raw_bytes.hex()


def _get_decoder_for_packet(packet_name: str):
    """
    Given full __packet like 'RAW__TLM__EMULATOR__HEALTH_ADCS_EST_ATTITUDE_ANGLE',
    we want decoder module/function from health_decoders package.
    """
    parts = packet_name.split("__")
    if len(parts) < 4:
        raise DecoderNotFound(f"Unexpected packet name format: {packet_name}")

    # everything after 'EMULATOR__' is our 'core' name
    core_name = "__".join(parts[3:])  # HEALTH_ADCS_EST_ATTITUDE_ANGLE etc.

    module_name = f"netra_backend.health_decoders.{core_name}"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        raise DecoderNotFound(f"Decoder module not found: {module_name}") from e

    # Logic: try exact function name match first, then search for ANY function starting with HEALTH_
    func = getattr(module, core_name, None)
    
    if func is None:
        # Fallback: search the module for the first function starting with HEALTH_
        # (This handles cases like HEALTH_COMMS_S -> HEALTH_COMMS_SBAND_TM_PROP_QUEUE0)
        for attr_name in dir(module):
            if attr_name.startswith("HEALTH_"):
                candidate = getattr(module, attr_name)
                if callable(candidate):
                    logger.debug("Found alternative decoder function: %s in %s", attr_name, module_name)
                    func = candidate
                    break
    
    if func is None:
        raise DecoderNotFound(f"No valid decoder function found in {module_name}")

    return core_name, func


class HealthConsumerService:
    def __init__(self):
        self.health_packets = _get_health_packet_names()

        # RabbitMQ config
        self.rabbitmq_url = os.getenv(
            "RABBITMQ_URL",
            "amqp://Netra:netra%40123@127.0.0.1:5673/%2f?heartbeat=0",
        )
        # Input exchange (raw telemetry)
        self.input_exchange = os.getenv("RABBITMQ_EXCHANGE", "telemetry.raw")
        
        # Output exchange (decoded telemetry)
        self.output_exchange = os.getenv("RABBITMQ_OUTPUT_EXCHANGE", "telemetry.decoded")

        # We need a separate publisher channel (or reuse the consumer's connection carefully)
        # Ideally, we open one connection and share it, or open two. 
        # For simplicity in this structure, we'll establish a publisher connection/channel
        # inside _consume_once or keep a persistent one. Let's keep a dedicated publisher helper.
        self._publisher_channel = None


    def run_forever(self) -> None:
        """
        Main loop: connect to RabbitMQ, consume health queues, reconnect on failures.
        """
        while True:
            try:
                self._consume_once()
            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt: stopping health consumer")
                break
            except Exception as e:
                logger.exception(
                    "Top-level error in HealthConsumerService: %s. Reconnecting in 5s", e
                )
                time.sleep(5.0)

    def _consume_once(self) -> None:
        """
        One connection lifecycle: connect to RabbitMQ, set up consumers, start consuming.
        """
        logger.info("Connecting to RabbitMQ for health consumer: %s", self.rabbitmq_url)
        params = pika.URLParameters(self.rabbitmq_url)
        connection = pika.BlockingConnection(params)
        logger.info("Connecting to RabbitMQ for health consumer: %s", self.rabbitmq_url)
        params = pika.URLParameters(self.rabbitmq_url)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        
        # Setup publisher resources
        # Declare the output exchange (durable topic)
        channel.exchange_declare(
            exchange=self.output_exchange, 
            exchange_type='topic', 
            durable=True
        )
        self._publisher_channel = channel

        # We assume queues are already declared by ws_ingestor (pkt.<packet_name>).
        # Here we just start consuming those that correspond to health packets.
        for pkt_name in self.health_packets:
            queue_name = f"pkt.{pkt_name}"
            logger.info("Subscribing to queue %s for packet %s", queue_name, pkt_name)
            channel.basic_consume(
                queue=queue_name,
                on_message_callback=self._on_message,
                auto_ack=False,
            )

        logger.info("Starting RabbitMQ consuming loop for health packets")
        try:
            channel.start_consuming()
        finally:
            logger.warning("RabbitMQ consuming loop ended; closing connection")
            try:
                if connection and connection.is_open:
                    connection.close()
            except Exception:
                logger.exception("Error closing RabbitMQ connection")

    def _on_message(self, ch: pika.adapters.blocking_connection.BlockingChannel,
                    method: pika.spec.Basic.Deliver,
                    properties: pika.BasicProperties,
                    body: bytes) -> None:
        """
        Callback for each message from any health queue.
        """
        try:
            msg = json.loads(body.decode("utf-8"))
        except Exception as e:
            logger.exception("Failed to parse JSON from message: %s", e)
            # Nothing else we can do; ack to avoid poison loop
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        packet_name = msg.get("__packet", "<no __packet>")
        buffer_b64 = msg.get("buffer")

        if not buffer_b64:
            logger.warning("Message missing 'buffer' field for packet %s", packet_name)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Convert base64 buffer to hex string
        try:
            hex_str = _decode_buffer_to_hex(buffer_b64)
        except Exception as e:
            logger.exception("Error converting buffer to hex for packet %s", packet_name)
            # treat as decoder failed (can't even get hex)
        except Exception as e:
            logger.exception("Error converting buffer to hex for packet %s", packet_name)
            # Log error via logging, or publish to an error topic if desired.
            # For now, just ack and move on to prevent poison pill.
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Find decoder
        try:
            core_name, decoder_fn = _get_decoder_for_packet(packet_name)
        except DecoderNotFound as e:
            logger.warning("Decoder not found for packet %s: %s", packet_name, e)
            # CASE: decoder not present
        except DecoderNotFound as e:
            logger.warning("Decoder not found for packet %s: %s", packet_name, e)
            # You could publish a "decoder.error" event here
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Run decoder
        try:
            segments = decoder_fn(hex_str)
        except Exception as e:
            logger.exception("Decoder error for packet %s", packet_name)
            # CASE: decoder present but failed
        except Exception as e:
            logger.exception("Decoder error for packet %s", packet_name)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        if not segments:
            logger.info("Decoder returned no segments for packet %s", packet_name)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Publish decoded data to next exchange
        try:
            # Construct payload
            # "segments" is a List[Dict]. We wrap it.
            payload = {
                "meta": {
                    "packet_name": packet_name,
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
                },
                "data": segments
            }
            
            # Routing key could be the packet name or "decoded.<packet_name>"
            routing_key = packet_name
            
            self._publisher_channel.basic_publish(
                exchange=self.output_exchange,
                routing_key=routing_key,
                body=json.dumps(payload),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                    content_type='application/json'
                )
            )

            logger.info(
                "Published %d decoded rows to exchange '%s' key '%s'",
                len(segments),
                self.output_exchange,
                routing_key,
            )
        except Exception as e:
            logger.exception("Error publishing decoded message for packet %s", packet_name)
            # If we fail to publish, we should probably NACK so we retry
            # But for simplicity here, just logging. 

        # Finally, ack the message so it is removed from the queue
        ch.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    setup_logging()
    logger.info("Starting health_consumer service (RabbitMQ -> decoders -> Postgres)...")
    svc = HealthConsumerService()
    svc.run_forever()


if __name__ == "__main__":
    main()
