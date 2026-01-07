import requests
import time
import json
import socket
import threading
import binascii
from datetime import datetime
from typing import Optional, List

# --- CONFIG ---
URL = "http://localhost:2900/openc3-api/api"
TOKEN = "openc3service"  # Same token used successfully with JSON-RPC
HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json"
}
SCOPE = "DEFAULT"
LOGFILE = "raw_telemetry_packets.log"
INTERVAL = 0.1  # Seconds

# TCP target (C receiver)
TCP_HOST = "127.0.0.1"
TCP_PORT = 8129

# Define (target, packet) pairs to monitor  [unchanged]
PACKETS_TO_MONITOR = [
    ("EMULATOR", "106_FTM_DOWNLINK_DATA"),
    ("EMULATOR", "104_FTM_DOWNLINK_METADATA"),
    ("EMULATOR", "107_NOTIFICATION_PACKET"),
]

# Cache for last value (unchanged)
last_packet_hex = {}

# ---- constants for C -> OpenC3 reassembly (minimal) ----
MAGIC = b"\x98\xBA\x76"
HEADER_A_LEN = 24  # payload_len at [22..23], payload at 24
LEN_A_LSB = 22     # (as used by your receive_thread)
LEN_A_MSB = 23

HEADER_B_LEN = 23  # payload_len at [21..22], payload at 23
LEN_B_LSB = 21     # (as used by your transmit callback indexes)
LEN_B_MSB = 22

MAX_FRAME = 65535


# ==================== OpenC3 helpers ====================

def post_json(url: str, headers: dict, payload: dict) -> Optional[dict]:
    try:
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[OpenC3] HTTP error: {e}")
        try:
            print("[OpenC3] Response:", r.text)  # type: ignore
        except Exception:
            pass
        return None


def send_packet_to_openc3(hex_packet: str, idx: int = 0):
    """
    Forward ONE full frame to OpenC3 using the exact JSON-RPC/curl shape
    you provided:  EMULATOR FTM_SEND_DATA_PCKTS with FTM_PACKETS 0x<HEX>
    """
    command_str = f"EMULATOR FTM_SEND_DATA_PCKTS with FTM_PACKETS 0x{hex_packet}"
    payload = {
        "jsonrpc": "2.0",
        "method": "cmd",
        "params": [command_str],
        "id": 9000 + idx,
        "keyword_params": {"scope": SCOPE},
    }
    print(f"[C->OpenC3] CMD: id={9000 + idx}, {len(hex_packet)//2} bytes")
    resp = post_json(URL, HEADERS, payload)
    if resp is None:
        print("[C->OpenC3]   FAIL")
    else:
        print("[C->OpenC3]   OK")


def get_tlm_buffer(target, packet):
    payload = {
        "jsonrpc": "2.0",
        "method": "get_tlm_buffer",
        "params": [target, packet],
        "id": 1,
        "keyword_params": {"scope": SCOPE},
    }
    try:
        response = requests.post(URL, headers=HEADERS, json=payload, timeout=10)
        response.raise_for_status()
        return response.json().get("result", None)
    except Exception as e:
        print(f"[ERROR] {target}.{packet} -> {e}")
        return None


# ==================== TCP helpers ====================

def connect_tcp():
    """Try connecting to TCP receiver; retry until success."""
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((TCP_HOST, TCP_PORT))
            print(f"[INFO] Connected to TCP receiver at {TCP_HOST}:{TCP_PORT}")
            return sock
        except Exception as e:
            print(f"[WARN] TCP connect failed: {e}, retrying in 2s...")
            time.sleep(2)


# ==================== Frame extraction ====================

def _extract_one(acc: bytearray) -> Optional[bytes]:
    """
    Try to extract ONE complete frame from acc.
    Handles both indexing conventions seen in your C (23 or 24 byte header).
    Returns the frame bytes or None if incomplete/unsynced.
    """
    # Sync to MAGIC
    idx = acc.find(MAGIC)
    if idx == -1:
        if acc:
            print(f"[Reasm] Drop {len(acc)}B (no MAGIC)")
        acc.clear()
        return None
    if idx > 0:
        # discard until MAGIC
        del acc[:idx]

    # need at least the smaller header
    if len(acc) < min(HEADER_A_LEN, HEADER_B_LEN):
        return None

    # Try Scheme A (24-byte header; len at [22..23], payload at 24)
    if len(acc) >= HEADER_A_LEN:
        pay_len_a = acc[LEN_A_LSB] | (acc[LEN_A_MSB] << 8)
        tot_a = HEADER_A_LEN + pay_len_a
        if HEADER_A_LEN <= tot_a <= MAX_FRAME:
            if len(acc) >= tot_a:
                frame = bytes(acc[:tot_a])
                del acc[:tot_a]
                return frame
        else:
            # length looks wrong; try Scheme B by falling through
            pass

    # Try Scheme B (23-byte header; len at [21..22], payload at 23)
    if len(acc) >= HEADER_B_LEN:
        pay_len_b = acc[LEN_B_LSB] | (acc[LEN_B_MSB] << 8)
        tot_b = HEADER_B_LEN + pay_len_b
        if HEADER_B_LEN <= tot_b <= MAX_FRAME:
            if len(acc) >= tot_b:
                frame = bytes(acc[:tot_b])
                del acc[:tot_b]
                return frame

    # If we reach here but header is present and lengths look bad, desync by 1
    if len(acc) >= 4:
        del acc[0:1]
    return None


# ==================== Threads ====================

def c_reader_thread(sock: socket.socket):
    """
    Reads whatever the C library sends() on the socket, reassembles complete frames,
    and forwards each as hex to OpenC3 using the exact command shape required.
    """
    acc = bytearray()
    send_idx = 0
    sock.settimeout(1.0)
    print("[Reader] Started.")
    try:
        while True:
            try:
                chunk = sock.recv(65536)
            except socket.timeout:
                continue
            if not chunk:
                print("[Reader] TCP closed by peer.")
                break

            acc.extend(chunk)
            while True:
                frame = _extract_one(acc)
                if frame is None:
                    break
                hexpkt = binascii.hexlify(frame).decode("ascii").upper()
                # forward to OpenC3
                send_packet_to_openc3(hexpkt, send_idx)
                send_idx += 1
    except Exception as e:
        print(f"[Reader] Error: {e}")
    finally:
        try:
            sock.close()
        except Exception:
            pass
        print("[Reader] Stopped.")


def openc3_writer_loop(sock: socket.socket):
    """
    Original behavior: poll OpenC3 tlm and forward raw bytes to C over TCP.
    (Unchanged logic.)
    """
    print("[Writer] Started.")
    while True:
        timestamp = datetime.now().isoformat()
        for (target, packet) in PACKETS_TO_MONITOR:
            key = f"{target}.{packet}"
            result = get_tlm_buffer(target, packet)
            if not result:
                continue

            buffer_data = result.get("buffer")

            if isinstance(buffer_data, dict) and "raw" in buffer_data:
                try:
                    raw_bytes = bytes(buffer_data["raw"])
                    hex_str = raw_bytes.hex()

                    # same logic: log only if changed
                    if hex_str != last_packet_hex.get(key):
                        last_packet_hex[key] = hex_str
                        print(f"[RAW] {key}: {hex_str}")
                        with open(LOGFILE, "a") as f:
                            f.write(f"{timestamp} | {key} = {hex_str}\n")

                        # ---- send to TCP ----
                        try:
                            sock.sendall(raw_bytes)
                        except Exception as e:
                            print(f"[WARN] TCP send failed: {e}")
                            raise

                except Exception as e:
                    print(f"[DECODE ERROR] {key}: Failed to convert raw bytes - {e}")
            else:
                print(f"[WARN] Unexpected buffer format in {key}: {type(buffer_data)}")

        time.sleep(INTERVAL)


def main():
    print("[INFO] Starting raw packet logger + TCP forwarder (now bidirectional)")
    while True:
        tcp_sock = connect_tcp()

        # Start the new READER (C -> OpenC3) thread
        t = threading.Thread(target=c_reader_thread, args=(tcp_sock,), daemon=True)
        t.start()

        # Keep the original WRITER loop (OpenC3 -> C) in foreground
        try:
            openc3_writer_loop(tcp_sock)
        except KeyboardInterrupt:
            print("\n[INFO] Exiting cleanly.")
            return
        except Exception as e:
            print(f"[Bridge] Writer error: {e}. Reconnecting...")
            try:
                tcp_sock.close()
            except Exception:
                pass
            time.sleep(2)
            # loop and reconnect


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Exiting cleanly.")
