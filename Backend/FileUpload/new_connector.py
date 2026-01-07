# ==============================================================
#  openc3_bridge.py  — Optimized High-Speed Version
#  Author: ChatGPT (optimized for throughput)
# ==============================================================
import os
import socket
import requests
import json
import time
import binascii
import select
import threading
import concurrent.futures
from typing import Optional, Tuple
from queue import Queue, Empty

# ================== CONFIG ==================
TCP_BIND_HOST = "127.0.0.1"
TCP_BIND_PORT = 8129

C2_API_URL = os.getenv("C2_API_URL", "http://host.docker.internal:2900/openc3-api/api")

CMD_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "mos12345"
}
TLM_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "mos12345"
}

COMMAND_NAME = "EMULATOR FTM_SEND_DATA_PCKTS"
FIELD_NAME   = "FTM_PACKETS"

TLM_TARGET_PACKET = "EMULATOR 101_NOTIFICATION_PACKET"
POLL_INTERVAL_SEC = 0.1
CUT_LEN = 512
TLM_MAX_AGE_SEC = 30

# SatOS framing
HEADER_LEN = 25              # CHANGED: C header is now bytes 0..24 (25 bytes total)
MAGIC = b"\x98\xBA\x76"
MAX_FRAME_LEN = 65535

# Concurrency
MAX_WORKERS = 8
# ==============================================================


# ==============================================================
#                  Helper Utilities
# ==============================================================
def bytes_to_hex_upper(data: bytes) -> str:
    return binascii.hexlify(data).decode("ascii").upper()

def hex_preview(label: str, data: bytes, n: int = 64):
    h = bytes_to_hex_upper(data[:n])
    print(f"{label} ({len(data)} bytes): {h}{'...' if len(data)>n else ''}")

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS)
session.mount("http://", adapter)
session.mount("https://", adapter)

def post_json(url: str, headers: dict, payload: dict) -> Optional[dict]:
    try:
        r = session.post(url, headers=headers, data=json.dumps(payload), timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[Bridge] HTTP error: {e}")
        try:
            print("[Bridge] Response text:", r.text)
        except Exception:
            pass
        return None

def send_packet_to_openc3(hex_packet: str, idx: int = 0):
    command_str = f"{COMMAND_NAME} with {FIELD_NAME} 0x{hex_packet}"
    payload = {
        "jsonrpc": "2.0",
        "method": "cmd",
        "params": [ command_str ],
        "id": 9000 + idx,
        "keyword_params": {"scope": "DEFAULT"}
    }
    resp = post_json(C2_API_URL, CMD_HEADERS, payload)
    if resp is None:
        print(f"[Bridge] CMD FAIL id={9000+idx}")
    return resp

def _ns_str_to_epoch_secs(ns_str: str) -> Optional[float]:
    try:
        return int(ns_str) / 1_000_000_000.0
    except Exception:
        return None

def poll_tlm_once(last_count_seen: Optional[int]) -> Tuple[Optional[bytes], Optional[int]]:
    payload = {
        "jsonrpc": "2.0",
        "method": "get_tlm_buffer",
        "params": [ TLM_TARGET_PACKET ],
        "id": 42,
        "keyword_params": {"scope": "DEFAULT"}
    }
    resp = post_json(C2_API_URL, TLM_HEADERS, payload)
    if resp is None:
        return None, last_count_seen

    try:
        result = resp["result"]
        recv_count = int(result.get("received_count", "0"))
        ts_str = result.get("received_time") or result.get("time")
        ts_epoch = _ns_str_to_epoch_secs(ts_str) if ts_str else None
        now = time.time()
        age = (now - ts_epoch) if ts_epoch else None

        if last_count_seen is not None and recv_count <= last_count_seen:
            return None, last_count_seen
        if ts_epoch is None:
            return None, last_count_seen
        if (now - ts_epoch) > TLM_MAX_AGE_SEC:
            return None, last_count_seen

        raw = result["buffer"]["raw"]
        first = raw[:CUT_LEN]
        b = bytes((int(x) & 0xFF) for x in first)
        return b, recv_count
    except Exception as e:
        print(f"[Bridge] TLM parse error: {e}")
        try:
            print(f"[Bridge] Response causing error: {json.dumps(resp, indent=2)}")
        except:
            print(f"[Bridge] Raw response: {resp}")
        return None, last_count_seen


# ==============================================================
#                  Bridge Server Class
# ==============================================================
class BridgeServer:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.server_sock: Optional[socket.socket] = None
        self.client_sock: Optional[socket.socket] = None
        self.stop_flag = False

        self._acc = bytearray()
        self._lock = threading.Lock()

        self._tx_queue: "Queue[bytes]" = Queue()
        self._tlm_queue: "Queue[bytes]" = Queue()

        self._send_idx = 0

        self._poll_thread = None
        self._sender_thread = None
        self.last_tlm_count: Optional[int] = None

    # ---- framing helpers ----
    def _resync_to_magic(self) -> bool:
        idx = self._acc.find(MAGIC)
        if idx == -1:
            if len(self._acc) > 0:
                print(f"[Bridge] Resync: dropping {len(self._acc)} bytes (no MAGIC)")
            self._acc.clear()
            return False
        if idx > 0:
            del self._acc[:idx]
        return True

    def _extract_frames(self):
        made = 0
        while True:
            if len(self._acc) < HEADER_LEN:
                return made
            if not self._acc.startswith(MAGIC):
                if not self._resync_to_magic():
                    return made
                if len(self._acc) < HEADER_LEN:
                    return made

            # Match latest C header layout:
            #   buffer[23] = payload_len LSB
            #   buffer[24] = payload_len MSB
            #   payload starts at 25
            payload_len = self._acc[23] | (self._acc[24] << 8)
            total_len = HEADER_LEN + payload_len

            if total_len <= HEADER_LEN or total_len > MAX_FRAME_LEN:
                del self._acc[:1]
                continue

            if len(self._acc) < total_len:
                return made

            frame = bytes(self._acc[:total_len])
            del self._acc[:total_len]
            self._tx_queue.put(frame)
            made += 1

    # ---- concurrent sender thread ----
    def _sender_thread_func(self):
        print("[Bridge] Sender thread started (concurrent mode).")
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            while not self.stop_flag:
                try:
                    frame = self._tx_queue.get(timeout=0.05)
                except Empty:
                    continue
                hexpkt = bytes_to_hex_upper(frame)
                fut = executor.submit(send_packet_to_openc3, hexpkt, self._send_idx)
                futures.append(fut)
                self._send_idx += 1
                futures = [f for f in futures if not f.done()]
                self._tx_queue.task_done()
        print("[Bridge] Sender thread stopped.")

    # ---- telemetry poll thread ----
    def _poll_tlm_thread_func(self):
        print("[Bridge] Poll thread started.")
        last_seen = None
        while not self.stop_flag:
            b, new_count = poll_tlm_once(last_seen)
            if new_count is not None and (last_seen is None or new_count > last_seen):
                last_seen = new_count
                if b:
                    self._tlm_queue.put(b)
            time.sleep(POLL_INTERVAL_SEC)
        print("[Bridge] Poll thread stopped.")

    # ---- main server ----
    def start(self):
        self._poll_thread = threading.Thread(target=self._poll_tlm_thread_func, daemon=True)
        self._poll_thread.start()

        self._sender_thread = threading.Thread(target=self._sender_thread_func, daemon=True)
        self._sender_thread.start()

        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen(1)
        print(f"[Bridge] Listening on {self.host}:{self.port}")

        while not self.stop_flag:
            print("[Bridge] Waiting for TCP client...")
            try:
                self.client_sock, addr = self.server_sock.accept()
            except Exception:
                continue
            print(f"[Bridge] Client connected from {addr}")
            self.client_sock.setblocking(False)

            try:
                self.loop()
            except Exception as e:
                print(f"[Bridge] loop error: {e}")
            finally:
                try:
                    if self.client_sock:
                        self.client_sock.close()
                except Exception:
                    pass
                self.client_sock = None
                print("[Bridge] Client disconnected. Waiting for reconnect...")

    def loop(self):
        print("[Bridge] TCP loop running.")
        while not self.stop_flag and self.client_sock:
            rlist, _, _ = select.select([self.client_sock], [], [], 0.05)
            if self.client_sock in rlist:
                data = self.client_sock.recv(131072)
                if not data:
                    break
                with self._lock:
                    self._acc.extend(data)
                    made = self._extract_frames()

            try:
                b = self._tlm_queue.get_nowait()
                self.client_sock.sendall(b)
            except Empty:
                pass
            except Exception:
                break

        print("[Bridge] TCP loop ended.")


# ==============================================================
#                        MAIN ENTRY
# ==============================================================
if __name__ == "__main__":
    srv = BridgeServer(TCP_BIND_HOST, TCP_BIND_PORT)
    srv.start()
