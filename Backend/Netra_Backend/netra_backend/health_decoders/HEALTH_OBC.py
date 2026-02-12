import struct
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------
# MAPPINGS
# ---------------------------------------------------------------------
FSM_STATE_MAP = {
    0: "obc init state",
    1: "obc active power critical state",
    2: "obc active power safe state",
    3: "obc active power normal state",
    4: "obc power save state",
    5: "obc reset state",
    6: "obc error state",
}

RESET_CAUSE_MAP = {
    0: "Unknown reset",
    1: "Low power reset",
    2: "Window watchdog reset",
    3: "Independent watchdog reset",
    4: "Software reset",
    5: "Power ON power down reset",
    6: "External reset pin reset",
    7: "Brownout reset",
}


# ---------------------------------------------------------------------
# SPEC
# ---------------------------------------------------------------------
SPEC: Dict[str, Any] = {
    "name": "HEALTH_OBC",
    "expected_queue_id": 0,
    "common_header": {
        "skip_bytes": 26,
        "fields": [
            {"name": "Submodule_ID", "type": "UINT8"},
            {"name": "Queue_ID", "type": "UINT8"},
            {"name": "Number_of_Instances", "type": "UINT16_LE"},
        ],
    },
    # Fixed OBC instance part size (till Reserved4)
    "fixed_instance_bytes": 35,
    # Plausible epoch seconds window for the low32 part (adjust if needed)
    "epoch_min": int(datetime(2000, 1, 1, tzinfo=timezone.utc).timestamp()),
    "epoch_max": int(datetime(2100, 1, 1, tzinfo=timezone.utc).timestamp()),
}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _normalize_hex(hex_str: str) -> bytes:
    s = hex_str.replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "")
    if len(s) % 2 != 0:
        raise ValueError(f"Hex string has odd length: {len(s)}")
    return bytes.fromhex(s)


def _parse_common_header(data: bytes, spec: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    header = spec["common_header"]
    cursor = int(header["skip_bytes"])

    if len(data) < cursor + 4:
        raise ValueError("Not enough data for common header")

    out: Dict[str, Any] = {}
    for f in header["fields"]:
        t = f["type"]
        if t == "UINT8":
            out[f["name"]] = struct.unpack_from("<B", data, cursor)[0]
            cursor += 1
        elif t == "UINT16_LE":
            out[f["name"]] = struct.unpack_from("<H", data, cursor)[0]
            cursor += 2
        else:
            raise ValueError(f"Unsupported header type: {t}")

    return out, cursor


def _timestamp_u64_to_utc(ts_u64: int) -> Optional[datetime]:
    """
    Your dump shows timestamps like: a6 bd 7a 69 00 00 00 00
    i.e. uint64 where high32 = 0 and low32 = epoch seconds.
    """
    try:
        low32 = ts_u64 & 0xFFFFFFFF
        high32 = (ts_u64 >> 32) & 0xFFFFFFFF

        # Prefer the observed pattern: high32 == 0, low32 is epoch seconds
        if high32 == 0:
            return datetime.fromtimestamp(int(low32), tz=timezone.utc)

        # Fallback (rare): treat whole u64 as seconds
        return datetime.fromtimestamp(int(ts_u64), tz=timezone.utc)
    except Exception:
        return None


def _is_plausible_timestamp_marker(data: bytes, pos: int, spec: Dict[str, Any]) -> bool:
    """
    Marker = 8 bytes (uint64 LE) such that:
      - high32 == 0
      - low32 within [epoch_min, epoch_max]
    """
    if pos < 0 or pos + 8 > len(data):
        return False

    ts_u64 = struct.unpack_from("<Q", data, pos)[0]
    low32 = ts_u64 & 0xFFFFFFFF
    high32 = (ts_u64 >> 32) & 0xFFFFFFFF

    if high32 != 0:
        return False

    return spec["epoch_min"] <= low32 <= spec["epoch_max"]


def _find_next_timestamp_marker(data: bytes, start: int, spec: Dict[str, Any]) -> Optional[int]:
    last = len(data) - 8
    for i in range(start, last + 1):
        if _is_plausible_timestamp_marker(data, i, spec):
            return i
    return None


def _decode_u16le_array(buf: bytes) -> List[int]:
    n = len(buf) // 2
    if n <= 0:
        return []
    return list(struct.unpack_from("<" + "H" * n, buf, 0))


def _parse_fixed_instance(data: bytes, pos: int) -> Dict[str, Any]:
    """
    Fixed 35 bytes layout:
      0:  u64 timestamp (LE)
      8:  u8  fsm_state
      9:  u8  num_resets
      10: u16 io_err
      12: u8  sys_err
      13: f32 cpuUtil
      17: u32 i_ram_rem_heap
      21: u32 t_ram_rem_heap
      25: u32 t_uptime
      29: u8  t_reset_cause
      30: u8  task_count
      31..34: reserved1..4 (u8)
    """
    out: Dict[str, Any] = {}

    ts_u64 = struct.unpack_from("<Q", data, pos + 0)[0]
    out["Timestamp_Raw"] = ts_u64
    ts_dt = _timestamp_u64_to_utc(ts_u64)
    if ts_dt is not None:
        out["Timestamp_UTC"] = ts_dt

    fsm = struct.unpack_from("<B", data, pos + 8)[0]
    out["Fsm_State"] = fsm
    out["Fsm_State_Str"] = FSM_STATE_MAP.get(fsm, f"UNKNOWN({fsm})")

    out["Num_Resets"] = struct.unpack_from("<B", data, pos + 9)[0]
    out["Io_Err"] = struct.unpack_from("<H", data, pos + 10)[0]
    out["Sys_Err"] = struct.unpack_from("<B", data, pos + 12)[0]

    cpu = struct.unpack_from("<f", data, pos + 13)[0]
    out["Cpu_Util"] = cpu

    out["I_Ram_Rem_Heap"] = struct.unpack_from("<I", data, pos + 17)[0]
    out["T_Ram_Rem_Heap"] = struct.unpack_from("<I", data, pos + 21)[0]
    out["T_Uptime"] = struct.unpack_from("<I", data, pos + 25)[0]

    rc = struct.unpack_from("<B", data, pos + 29)[0]
    out["T_Reset_Cause"] = rc
    out["T_Reset_Cause_Str"] = RESET_CAUSE_MAP.get(rc, f"UNKNOWN({rc})")

    out["Task_Count"] = struct.unpack_from("<B", data, pos + 30)[0]

    out["Reserved1"] = struct.unpack_from("<B", data, pos + 31)[0]
    out["Reserved2"] = struct.unpack_from("<B", data, pos + 32)[0]
    out["Reserved3"] = struct.unpack_from("<B", data, pos + 33)[0]
    out["Reserved4"] = struct.unpack_from("<B", data, pos + 34)[0]

    return out


# ---------------------------------------------------------------------
# Decoder
# ---------------------------------------------------------------------
def _decode_obc(hex_str: str, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
        data = _normalize_hex(hex_str)
    except Exception as e:
        print(f"[ERROR] Invalid hex input: {e}")
        return []

    try:
        hdr, cursor = _parse_common_header(data, spec)
    except Exception as e:
        print(f"[ERROR] Failed parsing header: {e}")
        return []

    expected_q = spec.get("expected_queue_id")
    if expected_q is not None and hdr.get("Queue_ID") != expected_q:
        print(f"[WARN] Queue_ID mismatch: got {hdr.get('Queue_ID')} expected {expected_q}")

    count = int(hdr.get("Number_of_Instances", 0))
    if count <= 0:
        return []

    fixed_len = int(spec["fixed_instance_bytes"])
    segments: List[Dict[str, Any]] = []

    # Resync to first timestamp marker (in case cursor isn't exactly aligned)
    first = _find_next_timestamp_marker(data, cursor, spec)
    if first is None:
        # If we can't find marker, fallback to cursor
        first = cursor

    cursor = first

    for idx in range(count):
        if cursor + fixed_len > len(data):
            break

        # Ensure we are at an instance start; if not, find next marker
        if not _is_plausible_timestamp_marker(data, cursor, spec):
            nxt = _find_next_timestamp_marker(data, cursor + 1, spec)
            if nxt is None:
                break
            cursor = nxt
            if cursor + fixed_len > len(data):
                break

        row = dict(hdr)
        fixed = _parse_fixed_instance(data, cursor)
        row.update(fixed)

        after_fixed = cursor + fixed_len

        # Find next instance start (next timestamp marker)
        next_start = _find_next_timestamp_marker(data, after_fixed, spec)

        if next_start is None:
            extras = data[after_fixed:]
            row["Ipc_Fail_Counter_List"] = _decode_u16le_array(extras)
            segments.append(row)
            break

        extras = data[after_fixed:next_start]
        row["Ipc_Fail_Counter_List"] = _decode_u16le_array(extras)
        segments.append(row)

        cursor = next_start

    return segments


# ---------------------------------------------------------------------
# Pipeline entry-point
# ---------------------------------------------------------------------
def HEALTH_OBC(hex_str: str) -> List[Dict[str, Any]]:
    return _decode_obc(hex_str, SPEC)
