import struct
from datetime import datetime, timezone
from typing import Any, Dict, List


# ---------------------------------------------------------------------
# SPEC (only this changes per decoder)
# ---------------------------------------------------------------------
# Packet: ADCS_HM_RW_SPEED_CMD (Queue ID 24)
# Table 60: Segment format:
#   Operation Status (1)
#   Epoch Time (4)
#   Number of Reaction wheel N (1)  [doc says N=4 typically]
#   Commanded wheel speed array (2 * N)  (int16 each, RPM)
#
# Total segment length = 6 + 2*N (variable)
SPEC: Dict[str, Any] = {
    "name": "HEALTH_ADCS_RW_SPEED_CMD",
    "expected_queue_id": 24,
    "common_header": {
        "skip_bytes": 26,
        "fields": [
            {"name": "Submodule_ID", "type": "UINT8"},
            {"name": "Queue_ID", "type": "UINT8"},
            {"name": "Number_of_Instances", "type": "UINT16_LE"},
        ],
    },
}


# ---------------------------------------------------------------------
# Generic decode helpers (same across your decoders)
# ---------------------------------------------------------------------
class ByteReader:
    def __init__(self, data: bytes):
        self.data = data
        self.i = 0

    def remaining(self) -> int:
        return len(self.data) - self.i

    def skip(self, n: int) -> None:
        if self.i + n > len(self.data):
            raise ValueError("Not enough bytes to skip")
        self.i += n

    def _unpack(self, fmt: str, size: int):
        if self.i + size > len(self.data):
            raise ValueError("Not enough bytes to read")
        chunk = self.data[self.i : self.i + size]
        self.i += size
        return struct.unpack(fmt, chunk)[0]

    def u8(self) -> int:
        return self._unpack("<B", 1)

    def u16le(self) -> int:
        return self._unpack("<H", 2)

    def u32le(self) -> int:
        return self._unpack("<I", 4)

    def i16le(self) -> int:
        return self._unpack("<h", 2)


def _normalize_hex(hex_str: str) -> bytes:
    s = hex_str.replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "")
    if len(s) % 2 != 0:
        raise ValueError(f"Hex string has odd length: {len(s)}")
    return bytes.fromhex(s)


def _parse_common_header(reader: ByteReader, spec: Dict[str, Any]) -> Dict[str, Any]:
    header = spec["common_header"]
    reader.skip(int(header["skip_bytes"]))
    out: Dict[str, Any] = {}

    for f in header["fields"]:
        t = f["type"]
        if t == "UINT8":
            out[f["name"]] = reader.u8()
        elif t == "UINT16_LE":
            out[f["name"]] = reader.u16le()
        else:
            raise ValueError(f"Unsupported header type: {t}")

    return out


# ---------------------------------------------------------------------
# Pipeline entry-point function (KEEP THIS NAME)
# ---------------------------------------------------------------------
def HEALTH_ADCS_RW_SPEED_CMD(hex_str: str) -> List[Dict[str, Any]]:
    """
    Queue ID 24 (Commanded Reaction Wheel Speed)
    Variable-length segment per instance:
      - Operation_Status : uint8
      - Epoch_Time       : uint32 -> UTC datetime
      - N                : uint8 (# reaction wheels, typically 4)
      - Commanded RW speed array: N x int16 (RPM)
    """
    try:
        data = _normalize_hex(hex_str)
    except Exception as e:
        print(f"[ERROR] Invalid hex input: {e}")
        return []

    r = ByteReader(data)

    try:
        hdr = _parse_common_header(r, SPEC)
    except Exception as e:
        print(f"[ERROR] Failed parsing header: {e}")
        return []

    if hdr.get("Queue_ID") != SPEC["expected_queue_id"]:
        print(f"[WARN] Queue_ID mismatch: got {hdr.get('Queue_ID')} expected {SPEC['expected_queue_id']}")

    count = int(hdr.get("Number_of_Instances", 0))
    if count <= 0:
        return []

    segments: List[Dict[str, Any]] = []

    for idx in range(count):
        # Minimum bytes before we know N:
        # op(1) + epoch(4) + N(1) = 6
        if r.remaining() < 6:
            break

        start_i = r.i

        try:
            operation_status = r.u8()
            epoch = r.u32le()
            epoch_time_utc = datetime.fromtimestamp(int(epoch), tz=timezone.utc)

            n = r.u8()
            if r.remaining() < 2 * n:
                # truncated instance -> stop cleanly
                r.i = start_i
                break

            speeds: List[int] = []
            for _ in range(n):
                speeds.append(r.i16le())

            row: Dict[str, Any] = {
                **hdr,
                "Operation_Status": operation_status,
                "Epoch_Time_UTC": epoch_time_utc,
                "RW_Count_N": n,
            }

            # Store each wheel commanded speed in its own DB-friendly field
            for k, val in enumerate(speeds, start=1):
                row[f"RW_Cmd_Speed_{k}_RPM"] = val

            segments.append(row)

        except Exception as e:
            print(f"[ERROR] Failed parsing segment {idx}: {e}")
            break

    return segments
