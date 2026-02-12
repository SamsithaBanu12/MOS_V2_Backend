import struct
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------
# SPEC (only this changes per decoder)
# ---------------------------------------------------------------------
SPEC: Dict[str, Any] = {
    "name": "ADCS_HM_RW_CURRENT",
    "expected_queue_id": 2,
    "common_header": {
        "skip_bytes": 26,
        "fields": [
            {"name": "Submodule_ID", "type": "UINT8"},
            {"name": "Queue_ID", "type": "UINT8"},
            {"name": "Number_of_Instances", "type": "UINT16_LE"},
        ],
    },

    # Segment base per Table 22:
    #   OperationStatus (1)
    #   EpochTime (4)
    #   n (1)  (# reaction wheels; expected 4)
    #   RW currents array: n values, each uint16 RAW*0.1
    "segment_base": [
        {"name": "Operation_Status", "type": "UINT8"},
        {"name": "Epoch_Time_UTC", "type": "UINT32_LE", "transform": "EPOCH32_TO_UTC_DATETIME"},
        {"name": "RW_Count", "type": "UINT8"},
    ],

    # Variable part definition (array)
    "var_array": {
        "count_from": "RW_Count",
        "item": {"name_prefix": "Reaction_Wheel_Current_", "type": "UINT16_LE", "scale": 0.1, "unit": "A"},
        # If you want to enforce 4, keep it; otherwise set to None
        "expected_count": 4,
    },

    # Minimum bytes for the fixed part of segment: 1 + 4 + 1 = 6
    "segment_min_len_bytes": 6,
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
    raise ValueError(f"Unsupported type: {typ}")


def _apply_transform(val: Any, transform: Optional[str]) -> Any:
    if not transform:
        return val

    if transform == "EPOCH32_TO_UTC_DATETIME":
        # uint32 epoch seconds -> UTC datetime
        return datetime.fromtimestamp(int(val), tz=timezone.utc)

    raise ValueError(f"Unsupported transform: {transform}")


def _apply_scale(val: Any, scale: Optional[float]) -> Any:
    if scale is None:
        return val
    return val * float(scale)


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

    instances = int(hdr.get("Number_of_Instances", 0))
    if instances <= 0:
        return []

    segments: List[Dict[str, Any]] = []

    base_fields = spec["segment_base"]
    var_def = spec["var_array"]
    min_len = int(spec["segment_min_len_bytes"])

    for seg_idx in range(instances):
        if r.remaining() < min_len:
            break

        row = dict(hdr)
        start_i = r.i

        try:
            # Read fixed/base fields
            for f in base_fields:
                raw = _read_typed(r, f["type"])
                raw = _apply_transform(raw, f.get("transform"))
                raw = _apply_scale(raw, f.get("scale"))
                row[f["name"]] = raw

            # Read variable array
            count_from = var_def["count_from"]
            n = int(row.get(count_from, 0))

            expected_n = var_def.get("expected_count")
            if expected_n is not None and n != int(expected_n):
                # Spec says n is always 4; if not, warn but still try to parse what is present.
                print(f"[WARN] Segment {seg_idx}: RW_Count={n}, expected {expected_n}")

            item_def = var_def["item"]
            prefix = item_def["name_prefix"]
            item_type = item_def["type"]
            item_scale = item_def.get("scale")
            item_unit = item_def.get("unit")  # not used, but kept for readability

            # Each item is 2 bytes (UINT16) as per table, scaled by 0.1
            needed = 2 * n
            if r.remaining() < needed:
                raise ValueError(f"Not enough bytes for RW current array: need {needed}, have {r.remaining()}")

            for i in range(1, n + 1):
                v = _read_typed(r, item_type)
                v = _apply_scale(v, item_scale)
                row[f"{prefix}{i}"] = v

            segments.append(row)

        except Exception as e:
            print(f"[ERROR] Failed parsing segment {seg_idx}: {e}")
            # We can't know exact segment size if n is wrong, but best-effort:
            # rollback to start and break to avoid cascading misalignment.
            r.i = start_i
            break

    return segments


# ---------------------------------------------------------------------
# Pipeline entry-point function (keep name as needed by your dispatcher)
# ---------------------------------------------------------------------
def HEALTH_ADCS_RW_CURRENT(hex_str: str) -> List[Dict[str, Any]]:
    return _decode_from_spec(hex_str, SPEC)
