# netra_backend/openc3/streamer.py
import os
import sys
import time
import logging
from typing import Callable, Dict, List, Optional

from netra_backend.config import get_openc3_config

# This import must come *after* env vars are set, but we can adjust that in code.
from openc3.script.web_socket_api import StreamingWebSocketApi

logger = logging.getLogger(__name__)

PacketCallback = Callable[[Dict], None]


class OpenC3Streamer:
    """
    Simple, robust wrapper around StreamingWebSocketApi.

    - Config comes from environment via get_openc3_config()
    - Runs an infinite loop with reconnects
    - Calls user callback for every packet
    """

    def __init__(self, on_packet: PacketCallback):
        self.on_packet = on_packet
        self.cfg = get_openc3_config()
        self._ensure_env()

    def _ensure_env(self) -> None:
        """
        Make sure OPENC3_* env vars are set for StreamingWebSocketApi.
        """
        os.environ["OPENC3_SCOPE"] = self.cfg.scope
        os.environ["OPENC3_API_HOSTNAME"] = self.cfg.api_hostname
        os.environ["OPENC3_API_PORT"] = self.cfg.api_port
        os.environ["OPENC3_API_PASSWORD"] = self.cfg.api_password

        logger.info(
            "Configured OpenC3 env: scope=%s host=%s port=%s",
            self.cfg.scope,
            self.cfg.api_hostname,
            self.cfg.api_port,
        )

    def run_forever(self, reconnect_delay: float = 5.0) -> None:
        """
        Outer loop that *never dies* unless you Ctrl+C the process.
        """
        packets_to_stream: List[str] = self.cfg.packets_tlm + self.cfg.packets_cmd
        items_to_stream: List[str] = self.cfg.items_to_stream

        if not packets_to_stream and not items_to_stream:
            logger.error("No packets or items configured to stream. Exiting.")
            sys.exit(1)

        while True:
            try:
                self._stream_once(packets_to_stream, items_to_stream)
            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt received, shutting down gracefully.")
                break
            except Exception as e:
                logger.exception(
                    "Top-level OpenC3 streamer error: %s. Reconnecting in %.1fs",
                    e,
                    reconnect_delay,
                )
                time.sleep(reconnect_delay)

    def _stream_once(self, packets_to_stream: List[str], items_to_stream: List[str]) -> None:
        """
        Single connection lifecycle: connect → add packets → read until error.
        Any exception here is caught by run_forever() which reconnects.
        """
        logger.info("Connecting to OpenC3 StreamingWebSocketApi...")
        with StreamingWebSocketApi() as api:
            # Subscribe to packets or items (mirrors your original logic)
            if packets_to_stream:
                api.add(packets=packets_to_stream, start_time=None, end_time=None)
                logger.info(
                    "Subscribed to %d packets from OpenC3", len(packets_to_stream)
                )
            elif items_to_stream:
                api.add(items=items_to_stream, start_time=None, end_time=None)
                logger.info(
                    "Subscribed to %d items from OpenC3", len(items_to_stream)
                )

            logger.info("✅ Connected to OpenC3 – starting stream loop")

            while True:
                batch = api.read()  # blocking read from OpenC3

                if not batch:
                    # No data in this tick; avoid busy loop
                    time.sleep(0.05)
                    continue

                for pkt in batch:
                    pkt_name = pkt.get("__packet", "<no __packet field>")
                    logger.debug("📥 Received packet: %s", pkt_name)

                    try:
                        self.on_packet(pkt)
                    except Exception:
                        # We never want one bad callback to kill the stream
                        logger.exception(
                            "Error in on_packet callback for packet %s", pkt_name
                        )
