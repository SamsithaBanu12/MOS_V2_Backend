import base64, json, ssl, time, threading
from datetime import datetime, timezone
from typing import Callable, Optional, Dict
from .encryption import encrypt_frame
from .decryption_tm import decrypt_tm_frame

import paho.mqtt.client as mqtt
from sqlalchemy.orm import Session

from .settings import TOPIC_COSMOS_COMMAND, TOPIC_COSMOS_TELEMETRY
from .models import TOPIC_TO_MODEL, HEALTH_SBAND_LOG, HEALTH_XBAND_LOG
from .stats import Stats


def utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def hex_view(b: bytes, max_len: int = 1024) -> str:
    h = b.hex()
    return h if len(h) <= max_len else h[:max_len] + f"...({len(b)} bytes)"


# ──────────────────────────────────────────────────────────────────────────────
# BridgeRunner (per-station, A<->B bridge)
# ──────────────────────────────────────────────────────────────────────────────
class BridgeRunner:
    def __init__(
        self,
        station_id: str,
        b_host: str, b_port: int, b_user: str, b_pass: str,
        topic_uplink: str, topic_downlink: str,
        stats: Stats,
        on_status: Callable[[str, bool, str], None],   # which(A/B), ok, station_id
        on_event: Optional[Callable[[Dict, str], None]] = None
    ):
        self.station_id = station_id
        self.b_host, self.b_port = b_host, b_port
        self.b_user, self.b_pass = b_user, b_pass
        self.topic_uplink = topic_uplink
        self.topic_downlink = topic_downlink

        self.stats = stats
        self.on_status = on_status
        self.on_event = on_event

        self._thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        self.a_connected = False
        self.b_connected = False

    def connect(self, a_host: str, a_port: int, db_factory: Callable[[], Session]):
        if self._thread and self._thread.is_alive():
            return
        self.stop_event.clear()
        self._thread = threading.Thread(
            target=self._worker,
            args=(a_host, a_port, db_factory),
            daemon=True, name=f"BridgeThread-{self.station_id}"
        )
        self._thread.start()

    def disconnect(self):
        self.stop_event.set()

    def _log(self, db: Session, logical_topic: str, direction: str, payload: bytes,
             display_text: str, meta: dict, mqtt_topic: str | None):
        Model = TOPIC_TO_MODEL[logical_topic]
        row = Model(
            ts_utc=utc_now_iso(),
            direction=direction,
            bytes=len(payload),
            raw_blob=payload,
            display_text=display_text,
            meta_json=json.dumps(meta) if meta else None,
            station_id=self.station_id,
            mqtt_topic=mqtt_topic
        )
        db.add(row)
        db.commit()
        return row.id

    def _worker(self, a_host: str, a_port: int, db_factory: Callable[[], Session]):
        client_a = mqtt.Client(userdata={})
        client_b = mqtt.Client(userdata={})
        client_a.user_data_set({"client_b": client_b})
        client_b.user_data_set({"client_a": client_a})

        # A callbacks
        def on_connect_a(client, userdata, flags, rc):
            ok = (rc == 0)
            self.a_connected = ok
            self.on_status("A", ok, self.station_id)
            if ok:
                client.subscribe(TOPIC_COSMOS_COMMAND)

        def on_disconnect_a(*_):
            self.a_connected = False
            self.on_status("A", False, self.station_id)

        def on_message_a(client, userdata, msg):
                raw = msg.payload or b""

                # Step 1: Convert the raw message to hex string
                raw_hex = raw.hex()

                # Step 2: Encrypt the raw message using the encrypt_frame function
                encrypted_hex = encrypt_frame(raw_hex)

                # Step 3: Base64 encode the encrypted message
                b64 = base64.b64encode(bytes.fromhex(encrypted_hex)).decode()

                # Step 4: Create the JSON object with the encrypted and base64-encoded message
                out_json_str = json.dumps({"message": b64})
                out_json = out_json_str.encode()

                # Step 5: Publish the encrypted and base64-encoded message to the uplink topic
                peer = userdata["client_b"]
                peer.publish(self.topic_uplink, out_json)

                # Stats tracking
                self.stats.bump(self.station_id, TOPIC_COSMOS_COMMAND, "rx", len(raw))
                self.stats.bump(self.station_id, "SatOS/uplink", "tx", len(out_json))

                # Database logging
                db = db_factory()
                try:
                    self._log(db, TOPIC_COSMOS_COMMAND, "AtoB", raw, hex_view(raw),
                            {"dir": "AtoB"}, mqtt_topic=msg.topic)
                    self._log(db, "SatOS/uplink", "AtoB", out_json,
                            out_json_str if len(out_json_str) <= 1024 else out_json_str[:1024] + "...",
                            {"dir": "AtoB"}, mqtt_topic=self.topic_uplink)
                finally:
                    db.close()

                # Event notification (if any)
                if self.on_event:
                    self.on_event({"type": "message", "topic": TOPIC_COSMOS_COMMAND}, self.station_id)
                    self.on_event({"type": "message", "topic": "SatOS/uplink"}, self.station_id)


        # B callbacks
        def on_connect_b(client, userdata, flags, rc):
            ok = (rc == 0)
            self.b_connected = ok
            self.on_status("B", ok, self.station_id)
            if ok:
                client.subscribe(self.topic_downlink)

        def on_disconnect_b(*_):
            self.b_connected = False
            self.on_status("B", False, self.station_id)

        def on_message_b(client, userdata, msg):
            # count rx always (encrypted JSON from station/B)
            self.stats.bump(self.station_id, "SatOS/downlink", "rx", len(msg.payload))

            raw = None  # this will hold the final *decrypted* bytes we send to COSMOS

            try:
                # 1) Parse JSON from B
                obj = json.loads(msg.payload.decode())

                # 2) Base64 decode → encrypted frame bytes
                enc_bytes = base64.b64decode(obj["message"])

                # 3) Convert encrypted bytes to hex string
                enc_hex = enc_bytes.hex()

                # 4) Decrypt TM frame (hex in, hex out)
                dec_hex = decrypt_tm_frame(enc_hex)

                # 5) Convert decrypted hex back to bytes
                raw = bytes.fromhex(dec_hex)

            except Exception as e:
                # If anything goes wrong (bad JSON, bad base64, decryption error),
                # we just don't forward anything to COSMOS.
                # You might want to log this later.
                raw = None

            else:
                # 6) Forward decrypted bytes to COSMOS telemetry
                peer = userdata["client_a"]
                peer.publish(TOPIC_COSMOS_TELEMETRY, raw)
                self.stats.bump(self.station_id, TOPIC_COSMOS_TELEMETRY, "tx", len(raw))

            # 7) DB logging (same structure as before, but now `raw` is decrypted)
            db = db_factory()
            try:
                # Log what came from station B (still the JSON with base64(encrypted))
                self._log(
                    db,
                    "SatOS/downlink",
                    "BtoA",
                    msg.payload,
                    msg.payload.decode(errors="replace")[:2048],
                    {"dir": "BtoA"},
                    mqtt_topic=msg.topic,
                )

                # Log what we forwarded to COSMOS (only if decryption succeeded)
                if raw:
                    self._log(
                        db,
                        TOPIC_COSMOS_TELEMETRY,
                        "BtoA",
                        raw,
                        hex_view(raw),
                        {"dir": "BtoA"},
                        mqtt_topic=TOPIC_COSMOS_TELEMETRY,
                    )
            finally:
                db.close()

            if self.on_event:
                self.on_event({"type": "message", "topic": "SatOS/downlink"}, self.station_id)
                if raw:
                    self.on_event({"type": "message", "topic": TOPIC_COSMOS_TELEMETRY}, self.station_id)


        # wire up
        client_a.on_connect = on_connect_a
        client_a.on_disconnect = on_disconnect_a
        client_a.on_message = on_message_a

        client_b.on_connect = on_connect_b
        client_b.on_disconnect = on_disconnect_b
        client_b.on_message = on_message_b

        # connect
        client_a.connect(a_host, a_port)
        client_b.username_pw_set(self.b_user, self.b_pass)
        client_b.tls_set(cert_reqs=ssl.CERT_NONE)
        client_b.tls_insecure_set(True)
        client_b.connect(self.b_host, self.b_port)

        client_a.loop_start(); client_b.loop_start()
        try:
            while not self.stop_event.is_set():
                time.sleep(0.2)
        finally:
            client_a.loop_stop(); client_b.loop_stop()
            client_a.disconnect(); client_b.disconnect()
            self.on_status("A", False, self.station_id)
            self.on_status("B", False, self.station_id)


# ──────────────────────────────────────────────────────────────────────────────
# HealthRunner (per-station)
# ──────────────────────────────────────────────────────────────────────────────
class HealthRunner:
    """
    Connects to the station's health broker/port, subscribes to sband/xband,
    persists rows with station_id, and emits WS nudges.
    """
    def __init__(
        self,
        station_id: str,
        host: str,
        port: int,
        sband_topic: str,
        xband_topic: str,
        db_factory: Callable[[], Session],
        ws_nudge: Callable[[Dict], None],
    ):
        self.station_id = station_id
        self.host = host
        self.port = port
        self.sband_topic = sband_topic
        self.xband_topic = xband_topic
        self.db_factory = db_factory
        self.ws_nudge = ws_nudge

        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.client: Optional[mqtt.Client] = None

    def _persist(self, topic: str, payload: bytes):
        db = self.db_factory()
        try:
            Model = HEALTH_SBAND_LOG if topic == self.sband_topic else HEALTH_XBAND_LOG
            row = Model(
                ts_utc=utc_now_iso(),
                bytes=len(payload),
                raw_blob=payload,
                display_text=payload.decode("utf-8", errors="replace"),
                mqtt_topic=topic,
                station_id=self.station_id,
            )
            db.add(row)
            db.commit()
        finally:
            db.close()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe([(self.sband_topic, 0), (self.xband_topic, 0)])

    def _on_message(self, client, userdata, msg):
        try:
            self._persist(msg.topic, msg.payload or b"")
        finally:
            try:
                self.ws_nudge({"type": "health", "station": self.station_id, "topic": msg.topic})
            except Exception:
                pass

    def _worker(self):
        self.client = mqtt.Client()
        # If TLS/auth required for health broker, configure here.
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.connect(self.host, self.port)

        self.client.loop_start()
        try:
            while not self.stop_event.is_set():
                time.sleep(0.2)
        finally:
            self.client.loop_stop()
            self.client.disconnect()

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._worker, daemon=True, name=f"HealthRunner-{self.station_id}")
        self.thread.start()

    def stop(self):
        self.stop_event.set()
