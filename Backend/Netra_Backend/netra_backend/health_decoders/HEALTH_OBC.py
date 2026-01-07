# health_obc_decode_and_push.py
import re
import struct
from datetime import datetime
from typing import Any, Dict, List, Tuple

import psycopg2
from psycopg2.extras import execute_values

# -----------------------------
# DB CONFIG (your creds)
# -----------------------------
DB = {
    "host": "localhost",
    "port": 5432,
    "dbname": "centraDB",
    "user": "root",
    "password": "root",
}

TABLE_NAME = "HEALTH_OBC"

# -----------------------------
# MAPPINGS
# -----------------------------
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = None

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

TASK_STATUS_MAP = {
    0: "SUCCESS",
    1: "IPC_Fail_Count",
}

# Based on your sample (0x3D = 61). If your firmware is always 61 tasks, keep it fixed.
MAX_TASKS = 61


# -----------------------------
# BYTE HELPERS
# -----------------------------
def _clean_hex_string(hex_str: str) -> bytes:
    s = re.sub(r'[\s,"\']+', "", hex_str)
    if len(s) % 2 != 0:
        raise ValueError("Hex string has odd length after cleaning.")
    return bytes.fromhex(s)

def _need(buf: bytes, pos: int, n: int, where: str):
    if pos + n > len(buf):
        raise ValueError(
            f"Not enough bytes while reading {where}: need {n}, have {len(buf)-pos} (pos={pos})"
        )

def _u8(buf: bytes, pos: int, where="u8") -> Tuple[int, int]:
    _need(buf, pos, 1, where)
    return buf[pos], pos + 1

def _u16le(buf: bytes, pos: int, where="u16le") -> Tuple[int, int]:
    _need(buf, pos, 2, where)
    return int.from_bytes(buf[pos:pos+2], "little", signed=False), pos + 2

def _u32le(buf: bytes, pos: int, where="u32le") -> Tuple[int, int]:
    _need(buf, pos, 4, where)
    return int.from_bytes(buf[pos:pos+4], "little", signed=False), pos + 4

def _u64le(buf: bytes, pos: int, where="u64le") -> Tuple[int, int]:
    _need(buf, pos, 8, where)
    return int.from_bytes(buf[pos:pos+8], "little", signed=False), pos + 8

def _f32le(buf: bytes, pos: int, where="f32le") -> Tuple[float, int]:
    _need(buf, pos, 4, where)
    return struct.unpack("<f", buf[pos:pos+4])[0], pos + 4

def _fmt_ist(ts_seconds: int) -> str:
    if IST is not None:
        dt = datetime.fromtimestamp(ts_seconds, tz=IST)
    else:
        dt = datetime.fromtimestamp(ts_seconds)
    s = dt.strftime("%B %d, %Y %I:%M:%S %p")
    s = s.replace(" 0", " ")
    return s


# -----------------------------
# DECODER: HEALTH_OBC
# -----------------------------
def HEALTH_OBC(hex_str: str) -> List[Dict[str, Any]]:
    buf = _clean_hex_string(hex_str)
    pos = 0

    # 1) skip first 26 bytes
    _need(buf, pos, 26, "skip header 26 bytes")
    pos += 26

    # 2) submodule id (1 byte)
    submodule_id, pos = _u8(buf, pos, "Submodule ID")

    # 3) queue id (1 byte)
    queue_id, pos = _u8(buf, pos, "Queue ID")

    # 4) number of instances (2 bytes LE)
    inst_count, pos = _u16le(buf, pos, "Number of Instances")

    if inst_count == 0:
        return []

    def _base_segment() -> Dict[str, Any]:
        seg: Dict[str, Any] = {
            "Submodule_ID": submodule_id,
            "Queue_ID": queue_id,
            "Number_of_Instances": inst_count,

            "Timestamp": None,

            "FSM_State_Code": None,
            "FSM_State": None,

            "Number_of_Resets": None,
            "IO_Errors": None,
            "System_Errors": None,

            "CPU_Utilisation": None,
            "IRAM_Rem_Heap": None,
            "ERAM_Rem_Heap": None,

            "Uptime": None,

            "Reset_Cause_Code": None,
            "Reset_Cause": None,

            "Task_Count": None,
            "Parse_Error": None,
        }

        # Pre-create all task status columns for schema stability
        for i in range(MAX_TASKS):
            seg[f"Task_{i+1:02d}_Status"] = None

        return seg

    segments: List[Dict[str, Any]] = []

    for _inst_idx in range(inst_count):
        seg = _base_segment()

        # 1) timestamp (8 bytes LE, unix seconds)
        ts64, pos = _u64le(buf, pos, "Timestamp (u64)")
        seg["Timestamp"] = _fmt_ist(ts64)

        # 2) FSM state (1 byte)
        fsm_code, pos = _u8(buf, pos, "FSM State")
        seg["FSM_State_Code"] = fsm_code
        seg["FSM_State"] = FSM_STATE_MAP.get(fsm_code, f"UNKNOWN({fsm_code})")

        # 3) number of resets (1 byte)
        resets, pos = _u8(buf, pos, "Number of resets")
        seg["Number_of_Resets"] = resets

        # 4) IO errors (2 bytes LE)
        io_err, pos = _u16le(buf, pos, "I/O errors")
        seg["IO_Errors"] = io_err

        # 5) system errors (1 byte)
        sys_err, pos = _u8(buf, pos, "System errors")
        seg["System_Errors"] = sys_err

        # 6) CPU utilisation (float32 LE)
        cpu_util, pos = _f32le(buf, pos, "CPU utilisation")
        seg["CPU_Utilisation"] = cpu_util

        # 7) iram_rem_heap (u32 LE)
        iram, pos = _u32le(buf, pos, "IRAM rem heap")
        seg["IRAM_Rem_Heap"] = iram

        # 8) eram_rem_heap (u32 LE)
        eram, pos = _u32le(buf, pos, "ERAM rem heap")
        seg["ERAM_Rem_Heap"] = eram

        # 9) uptime (u32 LE)
        uptime, pos = _u32le(buf, pos, "Uptime")
        seg["Uptime"] = uptime

        # 10) reset cause (1 byte) + mapping
        reset_cause, pos = _u8(buf, pos, "Reset cause")
        seg["Reset_Cause_Code"] = reset_cause
        seg["Reset_Cause"] = RESET_CAUSE_MAP.get(reset_cause, f"UNKNOWN({reset_cause})")

        # 11) task count (1 byte)
        task_count, pos = _u8(buf, pos, "Task count")
        seg["Task_Count"] = task_count

        # 12) task statuses (task_count * 2 bytes LE)
        if task_count > MAX_TASKS:
            seg["Parse_Error"] = (
                f"Task_Count={task_count} exceeds MAX_TASKS={MAX_TASKS}. Capping to MAX_TASKS."
            )
            read_tasks = MAX_TASKS
        else:
            read_tasks = task_count

        for i in range(read_tasks):
            st, pos = _u16le(buf, pos, f"Task status[{i}]")
            seg[f"Task_{i+1:02d}_Status"] = TASK_STATUS_MAP.get(st, f"UNKNOWN({st})")

        # If packet includes more task statuses than MAX_TASKS, skip remaining bytes
        if task_count > MAX_TASKS:
            skip_bytes = (task_count - MAX_TASKS) * 2
            _need(buf, pos, skip_bytes, "Extra task statuses to skip")
            pos += skip_bytes

        segments.append(seg)

    return segments


# -----------------------------
# DB HELPERS (dynamic columns)
# -----------------------------
def _infer_pg_type(value: Any) -> str:
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int):
        return "BIGINT"
    if isinstance(value, float):
        return "DOUBLE PRECISION"
    return "TEXT"


def ensure_table_for_packet(conn, packet_table: str, sample_row: Dict[str, Any]) -> None:
    cols = []
    for k, v in sample_row.items():
        cols.append(f'"{k}" {_infer_pg_type(v)}')

    columns_sql = ", ".join(["id BIGSERIAL PRIMARY KEY", "created_at TIMESTAMPTZ DEFAULT NOW()"] + cols)
    create_sql = f'CREATE TABLE IF NOT EXISTS "{packet_table}" ({columns_sql});'

    with conn.cursor() as cur:
        cur.execute(create_sql)
    conn.commit()


def insert_rows(conn, packet_table: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return

    keys = list(rows[0].keys())
    cols_sql = ", ".join(f'"{k}"' for k in keys)
    values = [[r.get(k) for k in keys] for r in rows]

    sql = f'INSERT INTO "{packet_table}" ({cols_sql}) VALUES %s'
    with conn.cursor() as cur:
        execute_values(cur, sql, values)
    conn.commit()


# -----------------------------
# MAIN
# -----------------------------
def main():
    # Paste your FULL buffer here
    SAMPLE_HEX = """
    <PASTE FULL HEX STRING HERE>
    """

    segments = HEALTH_OBC(SAMPLE_HEX)
    print(f"Decoded segments: {len(segments)}")
    if segments:
        # quick sanity print
        s0 = segments[0]
        print("First segment preview:")
        for k in [
            "Submodule_ID", "Queue_ID", "Number_of_Instances",
            "Timestamp", "FSM_State_Code", "FSM_State",
            "Reset_Cause_Code", "Reset_Cause", "Task_Count", "Parse_Error"
        ]:
            print(f"  {k}: {s0.get(k)}")

    conn = psycopg2.connect(**DB)
    try:
        ensure_table_for_packet(conn, TABLE_NAME, segments[0] if segments else {"dummy": ""})
        insert_rows(conn, TABLE_NAME, segments)
        print(f'Inserted {len(segments)} rows into "{TABLE_NAME}".')
    finally:
        conn.close()


if __name__ == "__main__":
    main()
