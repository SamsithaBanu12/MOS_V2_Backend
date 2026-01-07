# netra_backend/services/ws_ingestor.py
import logging
from typing import Dict, List

from netra_backend.logging_config import setup_logging
from netra_backend.openc3.streamer import OpenC3Streamer
from netra_backend.config import get_openc3_config
from netra_backend.common.messaging.rabbitmq import RabbitMQPublisher

logger = logging.getLogger("ws_ingestor")


def handle_packet_factory(publisher: RabbitMQPublisher):
    """
    Returns a handle_packet function that publishes each packet to RabbitMQ.
    """

    def handle_packet(pkt: Dict) -> None:
        # Packet name from OpenC3
        pkt_name = pkt.get("__packet", "<no __packet field>")
        routing_key = pkt_name

        logger.info("Publishing packet to RabbitMQ: %s (RK=%s)", pkt_name, routing_key)

        # We send the packet as-is (no modification)
        publisher.publish_json(routing_key, pkt)

    return handle_packet


def main() -> None:
    setup_logging()
    logger.info("Starting ws_ingestor service (OpenC3 WebSocket -> RabbitMQ)...")

    # Create RabbitMQ publisher
    publisher = RabbitMQPublisher(exchange="telemetry.raw")

    # Use the same packet list that OpenC3Streamer uses, to create queues
    cfg = get_openc3_config()
    all_packets: List[str] = cfg.packets_tlm + cfg.packets_cmd
    publisher.setup_queues_for_packets(all_packets)

    # Build a callback that uses this publisher
    handle_packet = handle_packet_factory(publisher)

    # Start streaming from OpenC3
    streamer = OpenC3Streamer(on_packet=handle_packet)
    streamer.run_forever(reconnect_delay=5.0)


if __name__ == "__main__":
    main()
