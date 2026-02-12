import struct
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------
# "JSON-like" SPEC (edit this per decoder)
# ---------------------------------------------------------------------
SPEC: Dict[str, Any] = {
    "name": "HEALTH_ADCS_CSS_VECTOR",
    "common_header": {
        "skip_bytes": 26,
        "fields": [
            {"name": "Submodule_ID", "type": "UINT8"},
            {"name": "Queue_ID", "type": "UINT8"},
            {"name": "Number_of_Instances", "type": "UINT16_LE"},
        ],
    },
    # Repeating segment format (per instance)
    "segment": [
        {"name": "Operation_Status", "type": "UINT8"},
        # Keep the output key SAME as before: Epoch_Time_Human (UTC datetime)
        {"name": "Epoch_Time_Human", "type": "UINT32_LE", "transform": "EPOCH_TO_UTC_DATETIME"},
        {"name": "Sun_Vector_X", "type": "INT16_LE", "scale": 0.001},
        {"name": "Sun_Vector_Y", "type": "INT16_LE", "scale": 0.001},
        {"name": "Sun_Vector_Z", "type": "INT16_LE", "scale": 0.001},
    ],
    "segment_len_bytes": 11,
}


# ---------------------------------------------------------------------
# ByteReader + generic decode (reused across all decoders in THIS file)
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

    # Typed reads
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


def _read_typed(reader: ByteReader, typ: str) -> Any:
    """
    Extend this mapping as you meet more field types.
    """
    if typ == "UINT8":
        return reader.u8()
    if typ == "UINT16_LE":
        return reader.u16le()
    if typ == "UINT32_LE":
        return reader.u32le()
    if typ == "INT16_LE":
        return reader.i16le()
    raise ValueError(f"Unsupported type: {typ}")


def _apply_transform(val: Any, transform: Optional[str]) -> Any:
    if not transform:
        return val
    if transform == "EPOCH_TO_UTC_DATETIME":
        return datetime.fromtimestamp(int(val), tz=timezone.utc)
    raise ValueError(f"Unsupported transform: {transform}")


def _apply_scale(val: Any, scale: Optional[float]) -> Any:
    if scale is None:
        return val
    return val * float(scale)


def _apply_mapping(val: Any, mapping: Optional[Dict[Any, Any]]) -> Any:
    if not mapping:
        return val
    # mapping keys might be strings depending how you write it; handle both
    return mapping.get(val, mapping.get(str(val), val))


def _parse_common_header(reader: ByteReader, spec: Dict[str, Any]) -> Dict[str, Any]:
    header = spec["common_header"]
    reader.skip(int(header["skip_bytes"]))
    out: Dict[str, Any] = {}

    for f in header["fields"]:
        raw = _read_typed(reader, f["type"])
        raw = _apply_mapping(raw, f.get("mapping"))
        raw = _apply_scale(raw, f.get("scale"))
        raw = _apply_transform(raw, f.get("transform"))
        out[f["name"]] = raw

    return out


def _decode_from_spec(hex_str: str, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
        data = _normalize_hex(hex_str)
    except Exception as e:
        print(f"[ERROR] Invalid hex input: {e}")
        return []

    reader = ByteReader(data)

    try:
        hdr = _parse_common_header(reader, spec)
    except Exception as e:
        print(f"[ERROR] Failed parsing header: {e}")
        return []

    count = int(hdr.get("Number_of_Instances", 0))
    if count <= 0:
        print("[WARN] Number_of_Instances is zero. Skipping parsing.")
        return []

    seg_len = int(spec["segment_len_bytes"])
    seg_fields = spec["segment"]

    segments: List[Dict[str, Any]] = []

    for idx in range(count):
        if reader.remaining() < seg_len:
            break

        row = dict(hdr)  # copy header fields into each row

        try:
            # Read exactly seg_len bytes via field reads; field types must sum to seg_len.
            start_i = reader.i

            for f in seg_fields:
                raw = _read_typed(reader, f["type"])
                raw = _apply_mapping(raw, f.get("mapping"))
                raw = _apply_scale(raw, f.get("scale"))
                raw = _apply_transform(raw, f.get("transform"))
                row[f["name"]] = raw

            # Safety: ensure we consumed exactly seg_len bytes (helps catch spec mistakes)
            consumed = reader.i - start_i
            if consumed != seg_len:
                print(
                    f"[WARN] Segment {idx}: spec consumed {consumed} bytes but segment_len_bytes={seg_len}. "
                    f"(Check your field list/types.)"
                )
                # You can choose to break/continue; continue keeps pipeline resilient.

            segments.append(row)

        except Exception as e:
            print(f"[ERROR] Failed parsing segment {idx}: {e}")
            # If parsing fails mid-segment, you may want to resync to next segment boundary:
            # Move reader to start_i + seg_len
            try:
                reader.i = start_i + seg_len
            except Exception:
                pass
            continue

    return segments


# ---------------------------------------------------------------------
# Your pipeline calls this function name, unchanged
# ---------------------------------------------------------------------
def HEALTH_ADCS_CSS_VECTOR(hex_str: str) -> List[Dict[str, Any]]:
    return _decode_from_spec(hex_str, SPEC)
