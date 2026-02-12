import struct
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------
# Table 16 mapping (ONLY what you shared: 0..28)
# ---------------------------
EPS_SUBSYSTEM_ENUM_MAP: Dict[int, str] = {
    0: "Hold and Release Module",
    1: "Primary On - Board Controller",
    2: "Secondary On - Board Controller",
    3: "Primary Payload Server",
    4: "Secondary Payload Server",
    5: "Primary GPS",
    6: "Secondary GPS",
    7: "Primary ADCS",
    8: "Reserved",
    9: "Primary UHF",
    10: "Reserved",
    11: "Primary S-BAND",
    12: "Reserved",
    13: "Primary X-BAND",
    14: "Secondary X-BAND",
    15: "Primary Edge Server",
    16: "Secondary Edge Server",
    17: "Primary Thruster",
    18: "Reserved",
    19: "MSI",
    20: "SES - A",
    21: "SES - B",
    22: "SAS - A",
    23: "Burn Wire - 1",
    24: "SAS - B",
    25: "Burn Wire - 2",
    26: "Avionics",
    27: "Reserved",
    28: "Reserved",
}


# ---------------------------------------------------------------------
# SPEC (this is what you'll change for each decoder)
# ---------------------------------------------------------------------
SPEC: Dict[str, Any] = {
    "name": "HEALTH_EPS_SES_TEMP",          # packet/decoder name
    "expected_queue_id": 1,                # optional check
    "common_header": {
        "skip_bytes": 26,
        "fields": [
            {"name": "Submodule_ID", "type": "UINT8"},
            {"name": "Queue_ID", "type": "UINT8"},
            {"name": "Number_of_Instances", "type": "UINT16_LE"},
        ],
    },
    # Per-instance segment fields (Table 20)
    "segment": [
        {"name": "Epoch_Time_UTC", "type": "UINT64_LE", "transform": "EPOCH64_TO_UTC_DATETIME"},
        {"name": "SES_A_Subsystem_ID", "type": "UINT8", "map_name": "EPS_SUBSYSTEM"},
        {"name": "SES_A_Temperature_C", "type": "UINT8", "transform": "TEMP_U8_255_INVALID_AS_INT8"},
        {"name": "SES_B_Subsystem_ID", "type": "UINT8", "map_name": "EPS_SUBSYSTEM"},
        {"name": "SES_B_Temperature_C", "type": "UINT8", "transform": "TEMP_U8_255_INVALID_AS_INT8"},
    ],
    "segment_len_bytes": 12,  # 8 + 1 + 1 + 1 + 1
}


# ---------------------------------------------------------------------
# Generic decode helpers (same across your decoders)
# ---------------------------------------------------------------------
MAPS: Dict[str, Dict[Any, Any]] = {
    "EPS_SUBSYSTEM": EPS_SUBSYSTEM_ENUM_MAP
}


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

    def u64le(self) -> int:
        return self._unpack("<Q", 8)


def _normalize_hex(hex_str: str) -> bytes:
    s = hex_str.replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "")
    if len(s) % 2 != 0:
        raise ValueError(f"Hex string has odd length: {len(s)}")
    return bytes.fromhex(s)


def _apply_transform(val: Any, transform: Optional[str]) -> Any:
    if not transform:
        return val

    if transform == "EPOCH64_TO_UTC_DATETIME":
        if val == 0xFFFFFFFFFFFFFFFF:
            return None
        return datetime.fromtimestamp(int(val), tz=timezone.utc)

    if transform == "TEMP_U8_255_INVALID_AS_INT8":
        # 255 means invalid
        if int(val) == 255:
            return None
        # interpret remaining u8 as signed int8
        return struct.unpack("<b", bytes([int(val)]))[0]

    raise ValueError(f"Unsupported transform: {transform}")


def _apply_mapping(val: Any, map_name: Optional[str]) -> Any:
    if not map_name:
        return val
    m = MAPS.get(map_name)
    if not m:
        return val
    return m.get(val, f"UNKNOWN_{val}")


def _read_typed(reader: ByteReader, typ: str) -> Any:
    if typ == "UINT8":
        return reader.u8()
    if typ == "UINT16_LE":
        return reader.u16le()
    if typ == "UINT64_LE":
        return reader.u64le()
    raise ValueError(f"Unsupported type: {typ}")


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

    # Optional queue check (doesn't affect pipeline; just guards wrong routing)
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
                # If field is an ID and you want also decoded name:
                # Here we replace the ID field itself with the mapped name ONLY if you want that.
                # But your pipeline likely wants both. So we keep ID and add a *_Name field.
                if f.get("map_name"):
                    # keep original ID in field name, add <name>_Name
                    row[f["name"]] = raw if not isinstance(raw, str) else raw  # (raw is still numeric for IDs)
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
# Pipeline entry-point function (name as per your decoder module)
# ---------------------------------------------------------------------
def HEALTH_EPS_SES_TEMP(hex_str: str) -> List[Dict[str, Any]]:
    return _decode_from_spec(hex_str, SPEC)
