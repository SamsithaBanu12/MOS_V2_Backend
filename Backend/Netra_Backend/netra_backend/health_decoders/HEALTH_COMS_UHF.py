import struct
from datetime import datetime

# ---------------------------------------------------------
# Helpers to read from a hex string at *byte* offsets
# ---------------------------------------------------------

def _read_u8_at(hex_str, byte_offset):
    i = byte_offset * 2
    return int(hex_str[i:i+2], 16)

def _read_u16_at(hex_str, byte_offset):
    i = byte_offset * 2
    return struct.unpack('<H', bytes.fromhex(hex_str[i:i+4]))[0]

def _read_u32_at(hex_str, byte_offset):
    i = byte_offset * 2
    return struct.unpack('<I', bytes.fromhex(hex_str[i:i+8]))[0]

def _read_u64_at(hex_str, byte_offset):
    i = byte_offset * 2
    return struct.unpack('<Q', bytes.fromhex(hex_str[i:i+16]))[0]

# ---------------------------------------------------------
# Main parser: UHF_TM_PROP_QUEUE_ID (Queue ID = 0)
# ---------------------------------------------------------

def HEALTH_COMMS_UHF_TM_PROP_QUEUE0(hex_str):
    """
    Parse COMMS UHF_TM_PROP_QUEUE_ID (Queue ID = 0) health TM.

    Framing assumptions (consistent with other health decoders):
      - Submodule ID at byte 25  (hex index 50)
      - Queue ID      at byte 26 (hex index 52)
      - Num instances at bytes 27–28 (uint16, little-endian)
      - First instance starts at byte 29.

    Per-instance struct (s_comms_uhf_get_tm_prop_time):
      - uint64  time_stamp
      - uint8   on_count
      - uint8   off_count
      - uint16  (reserved)
      - uint8   (reserved)
      - uint8   (reserved)
      - uint8   state
      - uint16  beacon_tx_cnt
      - many reserved fields...
      - s_comms_uhf_tm_prop comms_uhf_tm_stor, which contains:
          * uint32 uptime
          * uint32 Reserved
          * uint32 uart1_rx_count
          * ...
          * uint32 packets_sent
          * uint32 packets_good
          * uint32 packets_rejected_checksum
          * uint32 data_tx_cnt
          * uint32 data_rx_cnt

    This function decodes for each instance:
      - Time_Stamp_Raw / Time_Stamp_Human (UTC)
      - On_Count, Off_Count, State, Beacon_Tx_Count
      - Uptime, UART1_RX_Count
      - Packets_Sent, Packets_Good, Packets_Rejected_Checksum
      - Data_Tx_Count, Data_Rx_Count
      - Plus some reserved/raw blocks for possible future use.
    """

    # Header layout up to "Number of instance"
    header_skip_len = 29  # bytes (0..28 inclusive)

    # Submodule / Queue ID
    submodule_id = int(hex_str[50:52], 16)
    queue_id     = int(hex_str[52:54], 16)

    # Number of instances (uint16) at bytes 27–28
    count_offset_hex = (header_skip_len - 2) * 2  # 27 * 2 = 54
    instance_count = struct.unpack(
        '<H',
        bytes.fromhex(hex_str[count_offset_hex:count_offset_hex + 4])
    )[0]

    if instance_count == 0:
        print("[WARN] UHF_TM_PROP: instance count is zero. Skipping parsing.")
        return []

    # Data payload starts at byte 29
    payload_start_byte = 25 + 4  # 25: submodule, 26: queue, 27–28: count, 29: data
    payload_start_hex  = payload_start_byte * 2

    # Each s_comms_uhf_get_tm_prop_time is 140 bytes (70 prefix + 70 UHF TM)
    PREFIX_BYTES = 70
    UHF_TM_BYTES = 70
    BYTES_PER_INSTANCE = PREFIX_BYTES + UHF_TM_BYTES  # 140

    total_needed_bytes = instance_count * BYTES_PER_INSTANCE
    total_available_bytes = (len(hex_str) - payload_start_hex) // 2

    if total_available_bytes < total_needed_bytes:
        print(
            f"[WARN] UHF_TM_PROP: payload truncated. "
            f"Have {total_available_bytes} bytes, need {total_needed_bytes} "
            f"for {instance_count} instances. Parsing what is available."
        )

    segments = []

    for idx in range(instance_count):
        inst_start_byte = payload_start_byte + idx * BYTES_PER_INSTANCE
        inst_start_hex  = inst_start_byte * 2
        inst_end_hex    = inst_start_hex + BYTES_PER_INSTANCE * 2

        if inst_end_hex > len(hex_str):
            print(
                f"[WARN] UHF_TM_PROP: instance {idx} truncated "
                f"(expected up to index {inst_end_hex}, len={len(hex_str)}). Stopping."
            )
            break

        inst_hex = hex_str[inst_start_hex:inst_end_hex]

        seg = {
            "Submodule_ID":        submodule_id,
            "Queue_ID":            queue_id,
            "Instance_Index":      idx,
            "Number_of_Instances": instance_count,
        }

        # --------------------------------------------
        # Prefix (s_comms_uhf_get_tm_prop_time header)
        # --------------------------------------------

        # 0–7: time_stamp (uint64)
        ts_raw = _read_u64_at(inst_hex, 0)
        seg["Time_Stamp_Raw"] = ts_raw
        try:
            seg["Time_Stamp_Human"] = datetime.utcfromtimestamp(ts_raw) \
                                          .strftime("%Y-%m-%d %H:%M:%S")
        except (OverflowError, OSError, ValueError):
            seg["Time_Stamp_Human"] = None

        # 8: on_count (uint8)
        seg["On_Count"] = _read_u8_at(inst_hex, 8)

        # 9: off_count (uint8)
        seg["Off_Count"] = _read_u8_at(inst_hex, 9)

        # 14: state (uint8)
        seg["State"] = _read_u8_at(inst_hex, 14)

        # 15–16: beacon_tx_cnt (uint16)
        seg["Beacon_Tx_Count"] = _read_u16_at(inst_hex, 15)

        # Just for completeness, you can keep the whole prefix as raw (optional)
        seg["Prefix_Raw_Hex"] = inst_hex[:PREFIX_BYTES * 2]

        # --------------------------------------------
        # Inner UHF TM struct: s_comms_uhf_tm_prop
        # starts at byte offset 70 in the instance
        # --------------------------------------------

        base = PREFIX_BYTES  # byte offset inside instance

        # 70 + 0..3 : uptime
        seg["UHF_Uptime_s"] = _read_u32_at(inst_hex, base + 0)

        # 70 + 8..11 : uart1_rx_count  (skip 4 bytes Reserved)
        seg["UHF_UART1_RX_Count"] = _read_u32_at(inst_hex, base + 8)

        # 70 + 37..40 : packets_sent
        seg["Packets_Sent"] = _read_u32_at(inst_hex, base + 37)

        # 70 + 45..48 : packets_good (skip 4 bytes Reserved)
        seg["Packets_Good"] = _read_u32_at(inst_hex, base + 45)

        # 70 + 49..52 : packets_rejected_checksum
        seg["Packets_Rejected_Checksum"] = _read_u32_at(inst_hex, base + 49)

        # 70 + 62..65 : data_tx_cnt (skip some reserved)
        seg["Data_Tx_Count"] = _read_u32_at(inst_hex, base + 62)

        # 70 + 66..69 : data_rx_cnt
        seg["Data_Rx_Count"] = _read_u32_at(inst_hex, base + 66)

        # Optionally keep the whole UHF TM struct raw
        seg["UHF_TM_Raw_Hex"] = inst_hex[PREFIX_BYTES * 2 : PREFIX_BYTES * 2 + UHF_TM_BYTES * 2]

        segments.append(seg)

    return segments
