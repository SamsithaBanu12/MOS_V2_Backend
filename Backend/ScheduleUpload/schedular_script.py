#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
schedular_script.py (full-header hex print)
"""

import json
import os
import re
import struct
import math
import time
from typing import List, Tuple, Dict, Any
import requests
import sys
from datetime import datetime

# ------------------------------------------------------------------
# 🔧 Dynamic Schedule File Selection
# Priority:
#   1️⃣ Command-line argument (python3 schedular_script.py path/to/schedule.json)
#   2️⃣ Environment variable (export SCHEDULE_FILE=path/to/schedule.json)
#   3️⃣ Default (schedule.json in current directory)
# ------------------------------------------------------------------
if len(sys.argv) > 1:
    SCHEDULE_FILE = sys.argv[1]
elif "SCHEDULE_FILE" in os.environ:
    SCHEDULE_FILE = os.environ["SCHEDULE_FILE"]
else:
    SCHEDULE_FILE = os.path.join(os.path.dirname(__file__), "schedule.json")
# ------------------------------------------------------------------


class _Tee:
    def __init__(self, *files):
        self._files = files

    def write(self, data):
        for f in self._files:
            try:
                f.write(data)
                f.flush()
            except Exception:
                pass

    def flush(self):
        for f in self._files:
            try:
                f.flush()
            except Exception:
                pass


# ---------------- Config ----------------
MAX_RECORDS_PER_565 = 40
MAX_EVENTS_PER_SEGMENT = 10  # set 60 if needed

OPEN_C3_URL = os.getenv("OPEN_C3_URL", "http://host.docker.internal:2900/openc3-api/api")
OPEN_C3_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "mos12345",
}

# OpenC3 wrapper (constants / defaults) – EXACTLY aligned with your curl examples
CSPHEADER = 0x98BA7600  # 4B
SOF1 = 0xA5             # 1B
SOF2 = 0xAA             # 1B
TC_CTRL = 0xB0          # 1B
OC3_QOS = 3             # 1B
OC3_SA_ID = 1           # 1B
OC3_DA_ID = 0x81        # 1B (DA_ID 0x81)
OC3_RM_ID = 4           # 1B

# Sequence numbers and TCIDs from your curl snippets
SEQ_565 = 0x0300        # 2B
SEQ_547 = 0x0300        # 2B
TCID_565 = 0x3502       # 2B (TC_DEFFERED_STRG_OPT)
TCID_547 = 0x2302       # 2B (TC_547)

TARGET_565 = "EMULATOR TC_DEFFERED_STRG_OPT"
TARGET_547 = "EMULATOR TC_547"
SCOPE = "DEFAULT"
SAT_ID = 0              # 1B
GND_ID = 0              # 1B


def now_epoch() -> int:
    return int(time.time())


# ---------------- Utils ----------------
def parse_hex_str(s: str) -> bytes:
    if not s:
        return b""
    s = s.strip()
    if not s:
        return b""
    cleaned = re.sub(r"[^0-9a-fA-F]", "", s.replace("0x", "").replace("0X", ""))
    if len(cleaned) % 2:
        cleaned = "0" + cleaned
    return bytes.fromhex(cleaned)


def to_u8(s_hex: str) -> int:
    return int(s_hex, 16) & 0xFF


def to_u16(s_hex: str) -> int:
    return int(s_hex, 16) & 0xFFFF


def to_u32(s_hex: str) -> int:
    return int(s_hex, 16) & 0xFFFFFFFF


def be_u16(n: int) -> bytes:
    return struct.pack(">H", n & 0xFFFF)


def be_u32(n: int) -> bytes:
    return struct.pack(">I", n & 0xFFFFFFFF)


def le_u16(n: int) -> bytes:
    return struct.pack("<H", n & 0xFFFF)


def le_u32(n: int) -> bytes:
    return struct.pack("<I", n & 0xFFFFFFFF)


def hexstr(b: bytes) -> str:
    return b.hex().upper()


def b2s(b: bytes) -> str:
    return " ".join(f"{x:02X}" for x in b)


def to_4bytes_from_hex(s: str) -> bytes:
    b = parse_hex_str(s or "")
    if len(b) < 4:
        b = b.ljust(4, b"\x00")
    elif len(b) > 4:
        b = b[:4]
    return b


def shrink_payload_to_lsb_bytes(payload_field: str) -> bytes:
    if not payload_field:
        return b""
    tokens = [t.strip() for t in payload_field.split(",") if t.strip()]
    out = bytearray()
    for tok in tokens:
        cleaned = re.sub(r"[^0-9a-fA-F]", "", tok.replace("0x", "").replace("0X", ""))
        if not cleaned:
            continue
        if len(cleaned) % 2 == 1:
            cleaned = "0" + cleaned
        lsb2 = cleaned[-2:]
        out.append(int(lsb2, 16))
    return bytes(out)


def u8_from_dec_or_hex(s: str) -> int:
    s = (s or "").strip()
    if s.isdigit():
        val = int(s, 10)
    else:
        s = s.lower().replace("0x", "")
        val = int(s, 16) if s else 0
    return val & 0xFF


# ---------------- Builders ----------------
def load_schedule(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("schedule.json must be a JSON array")
    return data


def build_565_pdus_and_index(
    entries: List[Dict[str, Any]]
) -> Tuple[
    List[bytes],
    List[List[Dict[str, Any]]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
]:
    storage_cursor = 0
    pdus: List[bytes] = []
    batches: List[List[Dict[str, Any]]] = []
    updated_entries: List[Dict[str, Any]] = []
    pdu_meta_list: List[Dict[str, Any]] = []

    for i in range(0, len(entries), MAX_RECORDS_PER_565):
        batch = entries[i: i + MAX_RECORDS_PER_565]
        pdu_offset = storage_cursor  # 4B BE

        records = []
        batch_with_computed = []
        records_meta = []
        for e in batch:
            radio_id = to_u8(e["RadioID"])
            # Only last byte from each 32-bit payload token
            payload = shrink_payload_to_lsb_bytes(e.get("Payload", ""))

            rec = struct.pack(">B", radio_id) + payload
            records.append(rec)

            records_meta.append(
                {
                    "RadioID_val": radio_id,
                    "RadioID_bytes": bytes([radio_id]),
                    "Payload_bytes": payload,
                }
            )

            payload_addr = storage_cursor + 1  # skip RadioID
            payload_len = len(payload)

            e2 = dict(e)
            e2["computed_addr"] = payload_addr
            e2["computed_len"] = payload_len
            batch_with_computed.append(e2)
            updated_entries.append(e2)

            storage_cursor += len(rec)

        records_blob = b"".join(records)
        total_len = len(records_blob)  # 2B LE

        # Build original PDU body
        pdu_body = be_u32(pdu_offset) + le_u16(total_len) + records_blob
        # Leading length = byte length of pdu_body (2B, LE)
        leading_len_val = len(pdu_body)
        leading_len_bytes = le_u16(leading_len_val)
        pdu = leading_len_bytes + pdu_body

        pdus.append(pdu)
        batches.append(batch_with_computed)

        pdu_meta_list.append(
            {
                "LeadingLen_val": leading_len_val,
                "LeadingLen_bytes": leading_len_bytes,
                "Offset_val": pdu_offset,
                "Offset_bytes": be_u32(pdu_offset),
                "TotalLen_val": total_len,
                "TotalLen_bytes": le_u16(total_len),
                "Records_meta": records_meta,
            }
        )

    return pdus, batches, updated_entries, pdu_meta_list


def group_by_lut(entries: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
    out: Dict[int, List[Dict[str, Any]]] = {}
    for e in entries:
        s = str(e["LookUpTableID"])
        lut = int(s, 10) if re.fullmatch(r"\d+", s) else int(s, 16)
        out.setdefault(lut, []).append(e)
    return out


def build_547_event_blocks(
    entries: List[Dict[str, Any]]
) -> List[Tuple[bytes, Dict[str, Any]]]:
    """
    Build 547 EVENT blocks by taking Offset/Length EXACTLY from schedule (raw 4 bytes),
    encoding timestamp LE, TCID BE; print values as LE integers.

    IMPORTANT:
    - We use e["Timestamp"] directly as the FINAL execution time (epoch).
    - Any 'Delay' field in the schedule is ignored here (it's for UI / operator only).
    """
    results: List[Tuple[bytes, Dict[str, Any]]] = []
    by_lut = group_by_lut(entries)

    for lut_id, items in by_lut.items():
        total_events = len(items)
        total_segments = math.ceil(total_events / MAX_EVENTS_PER_SEGMENT)

        for seg_idx in range(total_segments):
            seg_items = items[
                seg_idx * MAX_EVENTS_PER_SEGMENT: (seg_idx + 1) * MAX_EVENTS_PER_SEGMENT
            ]
            seg_count = len(seg_items)

            h_bytes = struct.pack(
                ">BBBBB",
                lut_id & 0xFF,
                total_segments & 0xFF,
                seg_idx & 0xFF,
                0x00,
                seg_count & 0xFF,
            )

            infos = []
            printable_events = []
            for e in seg_items:
                # Use schedule Timestamp directly (epoch) – do NOT add Delay here
                ts = int(e["Timestamp"], 10)

                # 1B fields and TCID
                ms = 0
                # ONLY SrcID uses decimal-or-hex parsing
                src = u8_from_dec_or_hex(e["SrcID"])
                # Others remain as before (hex strings)
                dst = to_u8(e["DestID"])
                tcid = to_u16(e["TCID"])

                # Addr/Len: TAKE EXACTLY AS SCHEDULED (raw 4 bytes)
                addr_bytes = to_4bytes_from_hex(e.get("Offset", "00000000"))
                len_bytes = to_4bytes_from_hex(e.get("Length", "00000000"))

                # Value view for prints (LE interpretation)
                addr_val = int.from_bytes(addr_bytes, "little")
                length_val = int.from_bytes(len_bytes, "little")

                # Build bytes
                ts_bytes = le_u32(ts)  # LE
                ms_bytes = bytes([ms])
                src_bytes = bytes([src])
                dst_bytes = bytes([dst])
                tcid_bytes = be_u16(tcid)  # BE

                info = (
                    ts_bytes
                    + ms_bytes
                    + src_bytes
                    + dst_bytes
                    + tcid_bytes
                    + addr_bytes
                    + len_bytes
                )
                infos.append(info)

                printable_events.append(
                    {
                        "Timestamp_val": ts,
                        "Timestamp_bytes": ts_bytes,
                        "Millisecond_val": ms,
                        "Millisecond_bytes": ms_bytes,
                        "SrcID_val": src,
                        "SrcID_bytes": src_bytes,
                        "DestID_val": dst,
                        "DestID_bytes": dst_bytes,
                        "TCID_val": tcid,
                        "TCID_bytes": tcid_bytes,
                        "PayloadAddr_val": addr_val,
                        "PayloadAddr_bytes": addr_bytes,
                        "PayloadLen_val": length_val,
                        "PayloadLen_bytes": len_bytes,
                    }
                )

            block = h_bytes + b"".join(infos)
            results.append(
                (
                    block,
                    {
                        "LUT_ID_val": lut_id,
                        "LUT_ID_bytes": h_bytes[0:1],
                        "TotalSegments_val": total_segments,
                        "TotalSegments_bytes": h_bytes[1:2],
                        "SegmentID_val": seg_idx,
                        "SegmentID_bytes": h_bytes[2:3],
                        "Reserved_val": 0,
                        "Reserved_bytes": h_bytes[3:4],
                        "EventsInSegment_val": seg_count,
                        "EventsInSegment_bytes": h_bytes[4:5],
                        "Events": printable_events,
                    },
                )
            )

    return results


# ---------------- OpenC3 senders ----------------
def send_565(pdu_hex: str) -> None:
    """
    Send EMULATOR TC_DEFFERED_STRG_OPT command to OpenC3.
    This builds the SAME JSON as your curl, with dynamic TIMESTAMP (hex) and PDU.
    """
    # Hex timestamp like 0xAACD1A69
    ts_hex = f"0x{now_epoch():08X}"

    command_str = (
        "EMULATOR TC_DEFFERED_STRG_OPT with "
        f"CSPHEADER 0x{CSPHEADER:08X}, "
        f"SOF1 0x{SOF1:02X}, "
        f"SOF2 0x{SOF2:02X}, "
        f"TC_CTRL 0x{TC_CTRL:02X}, "
        f"TIMESTAMP {ts_hex}, "
        f"SEQ_NO 0x{SEQ_565:04X}, "
        f"SAT_ID {SAT_ID}, "
        f"GND_ID {GND_ID}, "
        f"QOS {OC3_QOS}, "
        f"SA_ID {OC3_SA_ID}, "
        f"DA_ID 0x{OC3_DA_ID:02X}, "
        f"RM_ID {OC3_RM_ID}, "
        f"TC_ID 0x{TCID_565:04X}, "
        f"PDU 0x{pdu_hex}"
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "cmd",
        "params": [command_str],
        "id": 9,
        "keyword_params": {"scope": SCOPE},
    }

    try:
        requests.post(OPEN_C3_URL, headers=OPEN_C3_HEADERS, json=payload, timeout=10)
    except Exception:
        pass


def send_547(event_hex: str, tc_len: int) -> None:
    """
    Send EMULATOR TC_547 command to OpenC3.
    Matches your curl format exactly, with dynamic TIMESTAMP, TC_LEN and EVENT.
    """
    # Hex timestamp like 0xAACD1A69
    ts_hex = f"0x{now_epoch():08X}"

    command_str = (
        "EMULATOR TC_547 with "
        f"CSPHEADER 0x{CSPHEADER:08X}, "
        f"SOF1 0x{SOF1:02X}, "
        f"SOF2 0x{SOF2:02X}, "
        f"TC_CTRL 0x{TC_CTRL:02X}, "
        f"TIMESTAMP {ts_hex}, "
        f"SEQ_NO 0x{SEQ_547:04X}, "
        f"SAT_ID {SAT_ID}, "
        f"GND_ID {GND_ID}, "
        f"QOS {OC3_QOS}, "
        f"SA_ID {OC3_SA_ID}, "
        f"DA_ID 0x{OC3_DA_ID:02X}, "
        f"RM_ID {OC3_RM_ID}, "
        f"TC_ID 0x{TCID_547:04X}, "
        f"TC_LEN {tc_len}, "
        f"EVENT 0x{event_hex}"
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "cmd",
        "params": [command_str],
        "id": 9,
        "keyword_params": {"scope": SCOPE},
    }

    try:
        requests.post(OPEN_C3_URL, headers=OPEN_C3_HEADERS, json=payload, timeout=10)
    except Exception:
        pass


# ---------------- Header composer (for printing full hex) ----------------
def compose_header_bytes(
    timestamp_now: int, seq_no: int, tc_id: int
) -> Tuple[bytes, Dict[str, bytes]]:
    """
    Compose the OpenC3 header bytes with fixed sizes (for printing).
    DA_ID is treated as 1 byte here, consistent with your curl semantics.
    """
    parts = {
        "CSPHEADER": be_u32(CSPHEADER),                # 4B
        "SOF1": bytes([SOF1]),                         # 1B
        "SOF2": bytes([SOF2]),                         # 1B
        "TC_CTRL": bytes([TC_CTRL]),                   # 1B
        "TIMESTAMP": le_u32(timestamp_now),            # 4B
        "SEQ_NO": be_u16(seq_no),                      # 2B
        "SAT_ID": bytes([SAT_ID]),                     # 1B
        "GND_ID": bytes([GND_ID]),                     # 1B
        "QOS": bytes([OC3_QOS]),                       # 1B
        "SA_ID": bytes([OC3_SA_ID]),                   # 1B
        "DA_ID": bytes([OC3_DA_ID & 0xFF]),            # 1B
        "RM_ID": bytes([OC3_RM_ID]),                   # 1B
        "TC_ID": be_u16(tc_id),                        # 2B
    }
    header = b"".join(
        parts[k]
        for k in [
            "CSPHEADER",
            "SOF1",
            "SOF2",
            "TC_CTRL",
            "TIMESTAMP",
            "SEQ_NO",
            "SAT_ID",
            "GND_ID",
            "QOS",
            "SA_ID",
            "DA_ID",
            "RM_ID",
            "TC_ID",
        ]
    )
    return header, parts


# ---------------- Printers ----------------
def print_565_frame(
    meta: Dict[str, Any],
    batch: List[Dict[str, Any]],
    pdu_bytes: bytes,
    header_full: bytes,
    header_parts: Dict[str, bytes],
) -> None:
    print("----- 565 FRAME -----")
    print(
        f"Leading Length (2B, LE): 0x{meta['LeadingLen_val']:04X} ({meta['LeadingLen_val']})"
    )
    print(f"  bytes: {b2s(meta['LeadingLen_bytes'])}")
    print(
        f"Offset Address (4B, BE): 0x{meta['Offset_val']:08X} ({meta['Offset_val']})"
    )
    print(f"  bytes: {b2s(meta['Offset_bytes'])}")
    print(
        f"Total Length  (2B, LE): 0x{meta['TotalLen_val']:04X} ({meta['TotalLen_val']})"
    )
    print(f"  bytes: {b2s(meta['TotalLen_bytes'])}")
    for idx, (e, rmeta) in enumerate(zip(batch, meta["Records_meta"]), 1):
        rid = rmeta["RadioID_val"]
        payload = rmeta["Payload_bytes"]
        print(f"Record #{idx}:")
        print(f"  Radio ID (1B): 0x{rid:02X} ({rid})")
        print(f"    bytes: {b2s(rmeta['RadioID_bytes'])}")
        print(
            f"  TC Payload ({len(payload)} bytes): {payload.hex().upper() if payload else '(empty)'}"
        )
        if payload:
            print(f"    bytes: {b2s(payload)}")
    print("565 BODY HEX:")
    print(hexstr(pdu_bytes))
    print("565 FULL (Header + Body) HEX:")
    print(hexstr(header_full + pdu_bytes))
    print("565 HEADER BYTES (parts):")
    for k in [
        "CSPHEADER",
        "SOF1",
        "SOF2",
        "TC_CTRL",
        "TIMESTAMP",
        "SEQ_NO",
        "SAT_ID",
        "GND_ID",
        "QOS",
        "SA_ID",
        "DA_ID",
        "RM_ID",
        "TC_ID",
    ]:
        print(f"  {k}: {b2s(header_parts[k])}")
    print("---------------------")


def print_547_frame(
    meta: Dict[str, Any],
    event_bytes: bytes,
    tc_len: int,
    header_full: bytes,
    header_parts: Dict[str, bytes],
) -> None:
    print("----- 547 FRAME -----")
    print(
        f"ID of Look Up Table (1B): 0x{meta['LUT_ID_val'] & 0xFF:02X} ({meta['LUT_ID_val']})"
    )
    print(f"  bytes: {b2s(event_bytes[0:1])}")
    print(
        f"Total Segments (1B): 0x{meta['TotalSegments_val'] & 0xFF:02X} ({meta['TotalSegments_val']})"
    )
    print(f"  bytes: {b2s(event_bytes[1:2])}")
    print(
        f"Current Segment ID (1B): 0x{meta['SegmentID_val'] & 0xFF:02X} ({meta['SegmentID_val']})"
    )
    print(f"  bytes: {b2s(event_bytes[2:3])}")
    print(
        f"Reserved (1B): 0x{meta['Reserved_val'] & 0xFF:02X} ({meta['Reserved_val']})"
    )
    print(f"  bytes: {b2s(event_bytes[3:4])}")
    print(
        f"Events in Segment (1B): 0x{meta['EventsInSegment_val'] & 0xFF:02X} ({meta['EventsInSegment_val']})"
    )
    print(f"  bytes: {b2s(event_bytes[4:5])}")

    # Walk events (start after 5 bytes header)
    cursor = 5
    for i, ev in enumerate(meta["Events"], 1):
        print(f"Event #{i} (17 bytes):")
        ts_b = event_bytes[cursor: cursor + 4]
        cursor += 4
        ms_b = event_bytes[cursor: cursor + 1]
        cursor += 1
        src_b = event_bytes[cursor: cursor + 1]
        cursor += 1
        dst_b = event_bytes[cursor: cursor + 1]
        cursor += 1
        tcid_b = event_bytes[cursor: cursor + 2]
        cursor += 2
        addr_b = event_bytes[cursor: cursor + 4]
        cursor += 4
        len_b = event_bytes[cursor: cursor + 4]
        cursor += 4

        print(
            f"  Timestamp (4B, LE): 0x{ev['Timestamp_val']:08X} ({ev['Timestamp_val']})"
        )
        print(f"    bytes: {b2s(ts_b)}")
        print(
            f"  Millisecond (1B): 0x{ev['Millisecond_val'] & 0xFF:02X} ({ev['Millisecond_val']})"
        )
        print(f"    bytes: {b2s(ms_b)}")
        print(
            f"  SrcID (1B): 0x{ev['SrcID_val'] & 0xFF:02X} ({ev['SrcID_val']})"
        )
        print(f"    bytes: {b2s(src_b)}")
        print(
            f"  DestID (1B): 0x{ev['DestID_val'] & 0xFF:02X} ({ev['DestID_val']})"
        )
        print(f"    bytes: {b2s(dst_b)}")
        print(
            f"  TCID (2B, BE): 0x{ev['TCID_val'] & 0xFFFF:04X} ({ev['TCID_val']})"
        )
        print(f"    bytes: {b2s(tcid_b)}")
        print(
            f"  TC payload address (4B, LE): 0x{ev['PayloadAddr_val'] & 0xFFFFFFFF:08X} ({ev['PayloadAddr_val']})"
        )
        print(f"    bytes: {b2s(addr_b)}")
        print(
            f"  TC payload length  (4B, LE): 0x{ev['PayloadLen_val'] & 0xFFFFFFFF:08X} ({ev['PayloadLen_val']})"
        )
        print(f"    bytes: {b2s(len_b)}")

    print("547 BODY HEX (EVENT block):")
    print(hexstr(event_bytes))

    # TC_LEN shown and composed as LITTLE-ENDIAN in the reconstructed "full hex"
    print(f"TC_LEN (2B, LE) value: {tc_len}  bytes: {b2s(le_u16(tc_len))}")
    full = header_full + le_u16(tc_len) + event_bytes
    print("547 FULL (Header + TC_LEN + Body) HEX:")
    print(hexstr(full))

    print("547 HEADER BYTES (parts):")
    for k in [
        "CSPHEADER",
        "SOF1",
        "SOF2",
        "TC_CTRL",
        "TIMESTAMP",
        "SEQ_NO",
        "SAT_ID",
        "GND_ID",
        "QOS",
        "SA_ID",
        "DA_ID",
        "RM_ID",
        "TC_ID",
    ]:
        print(f"  {k}: {b2s(header_parts[k])}")
    print("---------------------")


# ---------------- Main ----------------
def main():
    # Enable tee so everything printed also goes to output.txt
    log_path = os.path.join(os.path.dirname(__file__), "output.txt")
    log_f = open(log_path, "w", encoding="utf-8")
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout = _Tee(sys.stdout, log_f)
    sys.stderr = _Tee(sys.stderr, log_f)
    print(
        f"=== Schedular run at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} ==="
    )
    print(f"Schedule file: {SCHEDULE_FILE}\n")

    try:
        entries = load_schedule(SCHEDULE_FILE)

        # Build 565 (also compute addresses/lengths for 547)
        pdus_565, batches_565, updated_entries, pdu_meta_list = build_565_pdus_and_index(
            entries
        )

        # Print + send 565
        for pdu_bytes, batch, meta in zip(pdus_565, batches_565, pdu_meta_list):
            ts_now = now_epoch()
            header_565, header_parts_565 = compose_header_bytes(
                ts_now, SEQ_565, TCID_565
            )
            print_565_frame(meta, batch, pdu_bytes, header_565, header_parts_565)
            try:
                send_565(hexstr(pdu_bytes))
            except Exception:
                pass

        # Build 547 blocks
        blocks_547 = build_547_event_blocks(updated_entries)

        # Print + send 547
        for event_bytes, meta in blocks_547:
            ts_now = now_epoch()
            header_547, header_parts_547 = compose_header_bytes(
                ts_now, SEQ_547, TCID_547
            )
            tc_len = len(event_bytes)
            print_547_frame(meta, event_bytes, tc_len, header_547, header_parts_547)
            try:
                send_547(hexstr(event_bytes), tc_len)
            except Exception:
                pass

        print(f"\n✅ Log saved to: {log_path}")

    finally:
        # Restore std streams and close file
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        try:
            log_f.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
