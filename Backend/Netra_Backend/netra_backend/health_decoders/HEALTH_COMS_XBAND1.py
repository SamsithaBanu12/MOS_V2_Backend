import struct
from datetime import datetime

# ---------------------------------------------------------
# Helpers to read from a hex string at *byte* offsets
# (byte offsets are relative to the local string we pass in)
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
    return struct.unpack('<Q', bytes.fromhex(s[i:i+16]))[0]

def _read_i32_at(hex_str, byte_offset):
    i = byte_offset * 2
    return struct.unpack('<i', bytes.fromhex(hex_str[i:i+8]))[0]

def _read_f64_at(hex_str, byte_offset):
    i = byte_offset * 2
    return struct.unpack('<d', bytes.fromhex(hex_str[i:i+16]))[0]


# ---------------------------------------------------------
# XBAND1 DATA QUEUE (Queue ID = 0) parser
# ---------------------------------------------------------

def HEALTH_COMMS_XBAND1_DATA_QUEUE0(hex_str):
    """
    Parse XBAND1_DATA_QUEUE_ID (Queue ID = 0) TM Get Health (Table 100).

    Framing assumptions (consistent with your other health decoders):
      - Submodule ID at byte 25  (hex index 50)
      - Queue ID      at byte 26 (hex index 52)
      - Number of instance at bytes 27–28 (uint16, little-endian)
      - From byte 29 onwards: 'instance_count' copies of
        s_comms_xband_get_tm_prop_time.

    Each instance is treated as:

        struct s_comms_xband_get_tm_prop_time {
            uint64_t            time_stamp;
            s_xband_periodic_tm comms_xband_tm_stor;
        };

    Inside s_xband_periodic_tm, we decode:
        - s_xband_cmn_tm:
            * temp_mcu, temp_fpga, temp_xcvr (int32, °C)
            * volt_vint, volt_vaux, volt_vbram,
              volt_vpint, volt_vpaux, volt_vpdro (double, V)
        - Tail:
            * on_count, off_count, state
        - Middle region (rx_tm[2], tx_tm, xmt_tm[2], and some reserved fields)
          is kept as raw hex (Middle_Block_Raw_Hex).

    Because the exact struct size in the manual is a bit inconsistent,
    this function infers 'bytes_per_instance' from the payload length
    and 'Number of instance' and then positions fields relative to that.
    """

    header_skip_len = 29  # bytes up to and including "Number of instance"

    # Submodule / Queue ID (absolute positions in the TM frame)
    submodule_id = int(hex_str[50:52], 16)
    queue_id     = int(hex_str[52:54], 16)

    # Number of instances at bytes 27–28
    count_offset_hex = (header_skip_len - 2) * 2  # 27 * 2 = 54
    instance_count = struct.unpack(
        '<H',
        bytes.fromhex(hex_str[count_offset_hex:count_offset_hex + 4])
    )[0]

    if instance_count == 0:
        print("[WARN] XBAND1_DATA: instance count is zero. Skipping parsing.")
        return []

    # Payload starts at byte 29
    payload_start_byte = 25 + 4  # 25: submodule, 26: queue, 27–28: count
    payload_start_hex  = payload_start_byte * 2

    total_payload_bytes = (len(hex_str) - payload_start_hex) // 2
    bytes_per_instance = total_payload_bytes // instance_count

    if bytes_per_instance == 0:
        print("[WARN] XBAND1_DATA: bytes_per_instance is zero. Nothing to parse.")
        return []

    # Layout inside each instance (relative to instance start, in BYTES):
    #   0–7 : uint64  time_stamp
    #   8.. : s_xband_periodic_tm
    #
    # Inside s_xband_periodic_tm:
    #   cmn_tm (s_xband_cmn_tm) is first:
    #       8+0  : int32 temp_mcu
    #       8+4  : int32 temp_fpga
    #       8+8  : int32 temp_xcvr
    #       8+12 : double volt_vint
    #       8+20 : double volt_vaux
    #       8+28 : double volt_vbram
    #       8+36 : double volt_vpint
    #       8+44 : double volt_vpaux
    #       8+52 : double volt_vpdro
    #     => cmn_tm size = 60 bytes (8..67)
    #
    # After cmn_tm come rx_tm[2], tx_tm, xmt_tm[2], then the tail.
    #
    # Tail size (fields after xmt_tm[2] in s_xband_periodic_tm):
    #   uint32  Reserved;                   4
    #   uint8   on_count;                   1
    #   uint8   off_count;                  1
    #   uint16  Reserved;                   2
    #   uint8   state;                      1
    #   uint16  Reserved x4;                8
    #   uint8   Reserved x9;                9
    #   uint16  Reserved;                   2
    #   uint8   Reserved x4;                4
    #   -----------------------------------------
    #   Tail total                            32 bytes
    #
    # So we know:
    #   MIN_HEAD = 8 (timestamp) + 60 (cmn_tm) = 68 bytes
    #   TAIL_BYTES = 32
    #
    # Unknown middle = bytes_per_instance - (MIN_HEAD + TAIL_BYTES)

    CMN_TM_OFFSET   = 8
    CMN_TM_SIZE     = 60
    MIN_HEAD_BYTES  = 8 + CMN_TM_SIZE     # time_stamp + cmn_tm
    TAIL_BYTES      = 32

    if bytes_per_instance < MIN_HEAD_BYTES:
        print(
            f"[WARN] XBAND1_DATA: bytes_per_instance ({bytes_per_instance}) "
            f"< minimum head ({MIN_HEAD_BYTES}); "
            "only decoding time_stamp & cmn_tm."
        )

    unknown_mid_bytes = max(0, bytes_per_instance - (MIN_HEAD_BYTES + TAIL_BYTES))

    segments = []

    for idx in range(instance_count):
        inst_start_hex = payload_start_hex + idx * bytes_per_instance * 2
        inst_end_hex   = inst_start_hex + bytes_per_instance * 2

        if inst_end_hex > len(hex_str):
            print(
                f"[WARN] XBAND1_DATA: instance {idx} truncated "
                f"(expected up to index {inst_end_hex}, len={len(hex_str)}). "
                "Stopping."
            )
            break

        inst_hex = hex_str[inst_start_hex:inst_end_hex]

        seg = {
            "Submodule_ID":        submodule_id,
            "Queue_ID":            queue_id,
            "Instance_Index":      idx,
            "Number_of_Instances": instance_count,
        }

        # 1) time_stamp (uint64 at byte 0)
        ts_raw = _read_u64_at(inst_hex, 0)
        seg["Time_Stamp_Raw"] = ts_raw
        try:
            seg["Time_Stamp_Human"] = datetime.utcfromtimestamp(ts_raw) \
                                          .strftime("%Y-%m-%d %H:%M:%S")
        except (OverflowError, OSError, ValueError):
            seg["Time_Stamp_Human"] = None

        # 2) s_xband_cmn_tm (temperatures & voltages)
        seg["Temp_MCU"]   = _read_i32_at(inst_hex, CMN_TM_OFFSET + 0)
        seg["Temp_FPGA"]  = _read_i32_at(inst_hex, CMN_TM_OFFSET + 4)
        seg["Temp_XCVR"]  = _read_i32_at(inst_hex, CMN_TM_OFFSET + 8)

        seg["Volt_VINT"]  = _read_f64_at(inst_hex, CMN_TM_OFFSET + 12)
        seg["Volt_VAUX"]  = _read_f64_at(inst_hex, CMN_TM_OFFSET + 20)
        seg["Volt_VBRAM"] = _read_f64_at(inst_hex, CMN_TM_OFFSET + 28)
        seg["Volt_VPINT"] = _read_f64_at(inst_hex, CMN_TM_OFFSET + 36)
        seg["Volt_VPAUX"] = _read_f64_at(inst_hex, CMN_TM_OFFSET + 44)
        seg["Volt_VPDRO"] = _read_f64_at(inst_hex, CMN_TM_OFFSET + 52)

        # 3) Middle block (rx_tm[2], tx_tm, xmt_tm[2], & some reserved) as raw hex
        middle_start_byte = MIN_HEAD_BYTES
        middle_end_byte   = MIN_HEAD_BYTES + unknown_mid_bytes
        seg["Middle_Block_Raw_Hex"] = inst_hex[middle_start_byte*2:middle_end_byte*2]

        # 4) Tail (on_count, off_count, state, + some reserved)
        if bytes_per_instance >= MIN_HEAD_BYTES + TAIL_BYTES:
            b = MIN_HEAD_BYTES + unknown_mid_bytes  # starting byte for tail

            # uint32 Reserved
            seg["Tail_Reserved0"] = _read_u32_at(inst_hex, b); b += 4

            seg["On_Count"]  = _read_u8_at(inst_hex, b); b += 1
            seg["Off_Count"] = _read_u8_at(inst_hex, b); b += 1

            seg["Tail_Reserved1"] = _read_u16_at(inst_hex, b); b += 2

            seg["State"] = _read_u8_at(inst_hex, b); b += 1

            # 4 * uint16 Reserved
            reserved16_block1 = []
            for _ in range(4):
                reserved16_block1.append(_read_u16_at(inst_hex, b))
                b += 2
            seg["Tail_Reserved16_Block1"] = reserved16_block1

            # 9 * uint8 Reserved
            reserved8_block1 = []
            for _ in range(9):
                reserved8_block1.append(_read_u8_at(inst_hex, b))
                b += 1
            seg["Tail_Reserved8_Block1"] = reserved8_block1

            # uint16 Reserved
            seg["Tail_Reserved2"] = _read_u16_at(inst_hex, b); b += 2

            # 4 * uint8 Reserved
            reserved8_block2 = []
            for _ in range(4):
                reserved8_block2.append(_read_u8_at(inst_hex, b))
                b += 1
            seg["Tail_Reserved8_Block2"] = reserved8_block2

        segments.append(seg)

    return segments
