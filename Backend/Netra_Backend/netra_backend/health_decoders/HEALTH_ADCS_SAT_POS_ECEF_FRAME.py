import struct
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------
# SPEC (only this changes per decoder)
# ---------------------------------------------------------------------
# Queue ID 30: ADCS_HM_SAT_POS_ECEF_FRAME
# Table 70: HM Satellite position in ECEF frame format (29 bytes)
#   - Operation Status (1)
#   - Epoch Time (4)
#   - ECEF X (double, 8)
#   - ECEF Y (double, 8)
#   - ECEF Z (double, 8)
SPEC: Dict[str, Any] = {
    "name": "HEALTH_ADCS_SAT_POS_ECEF_FRAME",
    "expected_queue_id": 30,
    "common_header": {
        "skip_bytes": 26,
        "fields": [
            {"name": "Submodule_ID", "type": "UINT8"},
            {"name": "Queue_ID", "type": "UINT8"},
            {"name": "Number_of_Instances", "type": "UINT16_LE"},
        ],
    },
    "segment": [
        {"name": "Operation_Status", "type": "UINT8"},
        {"name": "Epoch_Time_UTC", "type": "UINT32_LE", "transform": "EPOCH32_TO_UTC_DATETIME"},
        {"name": "ECEF_X", "type": "FLOAT64_LE"},
        {"name": "ECEF_Y", "type": "FLOAT64_LE"},
        {"name": "ECEF_Z", "type": "FLOAT64_LE"},
    ],
    "segment_len_bytes": 29,
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

    def _unpack(self, fmt: str, size: int) -> Any:
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

    def f64le(self) -> float:
        return self._unpack("<d", 8)


def _normalize_hex(hex_str: str) -> bytes:
    s = hex_str.replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "")
    if len(s) % 2 != 0:
        raise ValueError(f"Hex string has odd length: {len(s)}")
    return bytes.fromhex(s)


def _read_typed(reader: ByteReader, typ: str) -> Any:
    if typ == "UINT8":
        return reader.u8()
    if typ == "UINT16_LE":
        return reader.u16le()
    if typ == "UINT32_LE":
        return reader.u32le()
    if typ == "INT16_LE":
        return reader.i16le()
    if typ == "FLOAT64_LE":
        return reader.f64le()
    raise ValueError(f"Unsupported type: {typ}")


def _apply_transform(val: Any, transform: Optional[str]) -> Any:
    if not transform:
        return val
    if transform == "EPOCH32_TO_UTC_DATETIME":
        return datetime.fromtimestamp(int(val), tz=timezone.utc)
    raise ValueError(f"Unsupported transform: {transform}")


def _parse_common_header(reader: ByteReader, spec: Dict[str, Any]) -> Dict[str, Any]:
    header = spec["common_header"]
    reader.skip(int(header["skip_bytes"]))
    out: Dict[str, Any] = {}
    for f in header["fields"]:
        out[f["name"]] = _read_typed(reader, f["type"])
    return out


def _decode_from_spec(hex_str: str, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
        data = _normalize_hex(hex_str)
    except Exception as e:
        print(f"[ERROR] Invalid hex input: {e}")
        return []

    r = ByteReader(data)

    try:
        hdr = _parse_common_header(r, spec)
    except Exception as e:
        print(f"[ERROR] Failed parsing header: {e}")
        return []

    expected_q = spec.get("expected_queue_id")
    if expected_q is not None and hdr.get("Queue_ID") != expected_q:
        print(f"[WARN] Queue_ID mismatch: got {hdr.get('Queue_ID')} expected {expected_q}")

    count = int(hdr.get("Number_of_Instances", 0))
    if count <= 0:
        return []

    seg_len = int(spec["segment_len_bytes"])
    seg_fields = spec["segment"]

    segments: List[Dict[str, Any]] = []

    for idx in range(count):
        if r.remaining() < seg_len:
            break

        row = dict(hdr)
        start_i = r.i

        try:
            for f in seg_fields:
                raw = _read_typed(r, f["type"])
                raw = _apply_transform(raw, f.get("transform"))
                row[f["name"]] = raw

            consumed = r.i - start_i
            if consumed != seg_len:
                print(f"[WARN] Segment {idx}: consumed {consumed} bytes, expected {seg_len}")

            segments.append(row)

        except Exception as e:
            print(f"[ERROR] Failed parsing segment {idx}: {e}")
            r.i = start_i + seg_len
            continue

    return segments


# ---------------------------------------------------------------------
# Pipeline entry-point function (KEEP THIS NAME)
# ---------------------------------------------------------------------
def HEALTH_ADCS_SAT_POS_ECEF_FRAME(hex_str: str) -> List[Dict[str, Any]]:
    return _decode_from_spec(hex_str, SPEC)
