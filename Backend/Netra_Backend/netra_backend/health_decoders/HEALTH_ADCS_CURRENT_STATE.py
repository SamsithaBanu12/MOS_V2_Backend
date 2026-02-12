import struct
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union


# ---------------------------------------------------------------------
# Enum mappings (from the tables you provided)
# ---------------------------------------------------------------------
ORBIT_PROP_MODE_MAP: Dict[int, str] = {
    0: "ADCS_KEPLER",
    1: "ADCS_GRAVITY_POINT",
    2: "ADCS_GRAVITY_J2",
    3: "ADCS_GRAVITY_HARMONIC",
    4: "ADCS_SGP4",
    5: "ADCS_EXTERN_ACC",
    6: "ADCS_POLYNOMIAL",
    7: "ADCS_DEPRECATED",
    8: "ADCS_FILTER",
}

GAIN_INDEX_MAP: Dict[int, str] = {
    1: "Sun Pointing",
    2: "Target Tracking",
    3: "Fine Target Tracking",
}

INERTIA_INDEX_MAP: Dict[int, str] = {
    1: "Deployed",
    2: "Stowed",
    3: "Compromised",
}

ESTIMATION_MODE_MAP: Dict[int, str] = {
    1: "ADCS_EST_MODE_RAW",
    2: "ADCS_EST_MODE_FG_WO_IMU",
    3: "ADCS_EST_MODE_FG",
    4: "ADCS_EST_MODE_KALMAN",
    5: "ADCS_EST_MODE_KALMAN_B",
}

CONTROL_MODE_MAP: Dict[int, str] = {
    4: "ADCS_CTRL_MODE_THREE_AXIS",
    5: "ADCS_CTRL_MODE_SUN_POINTING",
    6: "ADCS_CTRL_MODE_NADIR_POINTING",
    7: "ADCS_CTRL_MODE_TARGET_TRACKING",
    8: "ADCS_CTRL_MODE_FINE_SUN_POINTING",
}

MAPS: Dict[str, Dict[int, str]] = {
    "ORBIT_PROP_MODE": ORBIT_PROP_MODE_MAP,
    "GAIN_INDEX": GAIN_INDEX_MAP,
    "INERTIA_INDEX": INERTIA_INDEX_MAP,
    "ESTIMATION_MODE": ESTIMATION_MODE_MAP,
    "CONTROL_MODE": CONTROL_MODE_MAP,
}


# ---------------------------------------------------------------------
# SPEC (only this changes per decoder)
#
# NOTE: Table 27 says STRUCT length 14, but Table 28 uses offsets up to 14,
# which implies total length = 15 bytes (0..14). So we decode 15 bytes.
# If payload is shorter, we stop cleanly.
# ---------------------------------------------------------------------
SPEC: Dict[str, Any] = {
    "name": "HEALTH_ADCS_CURRENT_STATE",
    "expected_queue_id": 6,
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
        {"name": "Attitude_Estimation_Mode", "type": "UINT8", "map_name": "ESTIMATION_MODE"},
        {"name": "Control_Mode", "type": "UINT8", "map_name": "CONTROL_MODE"},

        # Packed region at offset 7, total 6 bytes:
        # bits 0-1 reserved
        # bits 2-3 Moment of inertia index (2 bits)
        # bits 4-5 Gain index (2 bits)
        # bits 6.. reserved (rest of 48-bit block)
        {"name": "_Packed_Block_7_12", "type": "BYTES_6", "transform": "ADCS_STATE_PACKED_7_12"},

        # Byte 13: validity flags (bit6 time valid, bit7 attitude valid)
        {"name": "_Validity_Byte_13", "type": "UINT8", "transform": "ADCS_STATE_VALIDITY_BYTE_13"},

        # Byte 14: reference valid (bit0), orbit propagation mode (bits1-4), eclipse flag (bit5)
        {"name": "_Flags_Byte_14", "type": "UINT8", "transform": "ADCS_STATE_FLAGS_BYTE_14"},
    ],
    "segment_len_bytes": 15,
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
    if typ == "BYTES_6":
        return reader.read_bytes(6)
    raise ValueError(f"Unsupported type: {typ}")


def _apply_mapping(val: Any, map_name: Optional[str]) -> Any:
    if not map_name:
        return val
    m = MAPS.get(map_name)
    if not m:
        return val
    return m.get(int(val), f"UNKNOWN_{val}")


def _apply_transform(val: Any, transform: Optional[str]) -> Union[Any, Dict[str, Any]]:
    if not transform:
        return val

    if transform == "EPOCH32_TO_UTC_DATETIME":
        return datetime.fromtimestamp(int(val), tz=timezone.utc)

    if transform == "ADCS_STATE_PACKED_7_12":
        # val is 6 bytes (little-endian bitfield)
        packed = int.from_bytes(val, byteorder="little", signed=False)
        moi = (packed >> 2) & 0x3
        gain = (packed >> 4) & 0x3
        return {
            "Moment_Of_Inertia_Index": moi,
            "Moment_Of_Inertia_Index_Name": _apply_mapping(moi, "INERTIA_INDEX"),
            "Gain_Index": gain,
            "Gain_Index_Name": _apply_mapping(gain, "GAIN_INDEX"),
            "Packed_7_12_Raw": packed,
        }

    if transform == "ADCS_STATE_VALIDITY_BYTE_13":
        b = int(val) & 0xFF
        time_valid = (b >> 6) & 0x1
        att_valid = (b >> 7) & 0x1
        return {
            "Time_Validity_Flag": bool(time_valid),
            "Attitude_Validity_Flag": bool(att_valid),
            "Validity_Byte_13_Raw": b,
        }

    if transform == "ADCS_STATE_FLAGS_BYTE_14":
        b = int(val) & 0xFF
        ref_valid = (b >> 0) & 0x1
        orbit_mode = (b >> 1) & 0xF  # bits 1..4
        eclipse = (b >> 5) & 0x1
        return {
            "Reference_Validity_Flag": bool(ref_valid),
            "Orbit_Propagation_Mode": orbit_mode,
            "Orbit_Propagation_Mode_Name": _apply_mapping(orbit_mode, "ORBIT_PROP_MODE"),
            "Eclipse_Flag": bool(eclipse),  # 1=Eclipse, 0=Sun Exposure
            "Flags_Byte_14_Raw": b,
        }

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

                # mapping is for simple enum fields (1-byte)
                if f.get("map_name"):
                    row[f["name"]] = int(raw)
                    row[f["name"] + "_Name"] = _apply_mapping(raw, f.get("map_name"))
                    continue

                transformed = _apply_transform(raw, f.get("transform"))

                # If a transform returns a dict, merge it into the row
                if isinstance(transformed, dict):
                    row.update(transformed)
                else:
                    row[f["name"]] = transformed

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
def HEALTH_ADCS_CURRENT_STATE(hex_str: str) -> List[Dict[str, Any]]:
    return _decode_from_spec(hex_str, SPEC)
