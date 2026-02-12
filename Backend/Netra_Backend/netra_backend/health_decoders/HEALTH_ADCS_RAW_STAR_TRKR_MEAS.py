import struct
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------
# Enum mapping (Table 52: Star Tracker mode enumeration)
# ---------------------------------------------------------------------
STAR_TRACKER_MODE_MAP: Dict[int, str] = {
    0: "ADCS_STAR_MODE_TRACKING",
    1: "ADCS_STAR_MODE_LOST",
}


# ---------------------------------------------------------------------
# SPEC (only this changes per decoder)
# ---------------------------------------------------------------------
SPEC: Dict[str, Any] = {
    "name": "HEALTH_ADCS_RAW_STAR_TRKR_MEAS",
    "expected_queue_id": 20,
    "common_header": {
        "skip_bytes": 26,
        "fields": [
            {"name": "Submodule_ID", "type": "UINT8"},
            {"name": "Queue_ID", "type": "UINT8"},
            {"name": "Number_of_Instances", "type": "UINT16_LE"},
        ],
    },
    # Table 51: HM Raw star tracker measurement format (47 bytes)
    "segment": [
        {"name": "Operation_Status", "type": "UINT8"},
        {"name": "Epoch_Time_UTC", "type": "UINT32_LE", "transform": "EPOCH32_TO_UTC_DATETIME"},
        {"name": "Stars_Detected_Count", "type": "UINT8"},   # offset 5
        {"name": "Reserved_6_7", "type": "UINT16_LE"},      # offset 6..7
        {"name": "Stars_Identified_Count", "type": "UINT8"},# offset 8
        {"name": "Identification_Mode", "type": "UINT8", "map_name": "STAR_TRACKER_MODE"},  # offset 9
        {"name": "Reserved_10_46", "type": "BYTES_37"},     # offset 10..46
    ],
    "segment_len_bytes": 47,
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

    def read_bytes(self, n: int) -> bytes:
        if self.i + n > len(self.data):
            raise ValueError("Not enough bytes to read")
        b = self.data[self.i : self.i + n]
        self.i += n
        return b

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
    if typ == "BYTES_37":
        return reader.read_bytes(37)
    raise ValueError(f"Unsupported type: {typ}")


def _apply_transform(val: Any, transform: Optional[str]) -> Any:
    if not transform:
        return val

    if transform == "EPOCH32_TO_UTC_DATETIME":
        return datetime.fromtimestamp(int(val), tz=timezone.utc)

    raise ValueError(f"Unsupported transform: {transform}")


def _apply_mapping(val: Any, map_name: Optional[str]) -> Any:
    if not map_name:
        return val

    if map_name == "STAR_TRACKER_MODE":
        return STAR_TRACKER_MODE_MAP.get(int(val), f"UNKNOWN_{val}")

    return val


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

                if f.get("map_name"):
                    row[f["name"]] = int(raw)
                    row[f["name"] + "_Name"] = _apply_mapping(raw, f.get("map_name"))
                else:
                    row[f["name"]] = raw

            consumed = r.i - start_i
            if consumed != seg_len:
                print(f"[WARN] Segment {idx}: consumed {consumed} bytes, expected {seg_len}")

            segments.append(row)

        except Exception as e:
            print(f"[ERROR] Failed parsing segment {idx}: {e}")
            # resync to next segment boundary
            r.i = start_i + seg_len
            continue

    return segments


# ---------------------------------------------------------------------
# Pipeline entry-point function (KEEP THIS NAME)
# ---------------------------------------------------------------------
def HEALTH_ADCS_RAW_STAR_TRKR_MEAS(hex_str: str) -> List[Dict[str, Any]]:
    return _decode_from_spec(hex_str, SPEC)
