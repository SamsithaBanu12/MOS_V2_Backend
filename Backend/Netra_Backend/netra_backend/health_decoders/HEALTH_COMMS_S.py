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

def _read_i32_at(hex_str, byte_offset):
    i = byte_offset * 2
    return struct.unpack('<i', bytes.fromhex(hex_str[i:i+8]))[0]

def _read_f64_at(hex_str, byte_offset):
    i = byte_offset * 2
    return struct.unpack('<d', bytes.fromhex(hex_str[i:i+16]))[0]


# ---------------------------------------------------------
# SBAND TM PROP (Queue ID = 0) parser
# ---------------------------------------------------------

def HEALTH_COMMS_SBAND_TM_PROP_QUEUE0(hex_str):
    """
    Parse COMMS SBAND_TM_PROP_QUEUE_ID (Queue ID = 0) payload.

    Framing assumptions (same as other health decoders you’re using):
      - Submodule ID at byte 25  (hex index 50)
      - Queue ID      at byte 26 (hex index 52)
      - Num instances at bytes 27–28 (Uint16, little-endian)
      - Payload starting at byte 29:
            offset 0 : Submodule ID
            offset 1 : Queue ID
            offset 2 : Number of instances
            offset 4 : First instance of s_comms_sband_get_tm_prop_time

    From your struct:

        typedef struct {
            int32_t temp_mcu;
            int32_t temp_fpga;
            int32_t temp_xcvr;
            double  volt_vint;
            double  volt_vaux;
            double  volt_vbram;
            double  volt_vpint;
            double  volt_vpaux;
            double  volt_vpdro;
        } s_sband_cmn_tm;

        typedef struct { ... } s_sband_rx_tm;    // NA for mission (still occupies space)
        typedef struct { ... } s_sband_tx_tm;    // NA for mission
        typedef struct {
            uint32_t On       : 1;
            uint32_t Mod      : 4;
            uint32_t Fec      : 4;
            uint32_t Att      :10;
            uint32_t Reserved : 4;
        } s_sband_XMT_INF_STRUCT;

        typedef struct {
            s_sband_cmn_tm cmn_tm;
            s_sband_rx_tm  rx_tm[2];
            s_sband_tx_tm  tx_tm;
            s_sband_XMT_INF_STRUCT xmt_tm[2];
            uint32_t Reserved;
            uint8_t  on_count;
            uint8_t  off_count;
            uint16_t sband_reset_cnt;
            uint8_t  state;
            uint16_t beacon_tx_cnt;
            uint8_t  Reserved;
            uint8_t  Reserved;
            uint8_t  rx_port_value : 1;
            // ...many Reserved uint16/uint32/uint8...
            uint8_t  sband_eps_mode;
            // ...more Reserved...
        } s_sband_periodic_tm;

        typedef struct {
            uint64_t time_stamp;
            s_sband_periodic_tm comms_sband_tm_stor;
        } s_comms_sband_get_tm_prop_time;

    Because the exact on-wire size of s_sband_periodic_tm can change
    (and the table’s “156 bytes” doesn’t match the full struct),
    this function:
      - infers bytes_per_instance = total_payload_bytes / Number_of_instances
      - assumes field order exactly matches the struct you provided
      - decodes:
          * time_stamp
          * s_sband_cmn_tm (temps + voltages)
          * the tail scalars (on_count, off_count, sband_reset_cnt,
            state, beacon_tx_cnt, rx_port_value, sband_eps_mode)
      - exposes the middle “unknown” section as raw hex per instance.
    """

    # Bytes up to and including "Number of instances"
    header_skip_len = 29  # bytes

    # Submodule / Queue ID (same absolute positions as your other decoders)
    submodule_id = int(hex_str[50:52], 16)
    queue_id     = int(hex_str[52:54], 16)

    # Number of instances (Uint16) at bytes 27–28
    count_offset_hex = (header_skip_len - 2) * 2  # 27 * 2 = 54
    instance_count = struct.unpack(
        '<H', bytes.fromhex(hex_str[count_offset_hex:count_offset_hex + 4])
    )[0]

    if instance_count == 0:
        print("[WARN] SBAND_TM_PROP: instance count is zero. Skipping parsing.")
        return []

    # Payload (instances) start at byte 29
    payload_start_byte = 25 + 4  # 25: submodule; +1 queue; +2 instances; +1 -> 29
    payload_start_hex  = payload_start_byte * 2

    total_payload_bytes = (len(hex_str) - payload_start_hex) // 2
    bytes_per_instance = total_payload_bytes // instance_count

    if bytes_per_instance == 0:
        print("[WARN] SBAND_TM_PROP: bytes_per_instance is zero. Nothing to parse.")
        return []

    # Layout inside each instance (relative byte offsets)
    # --------------------------------------------------
    # 0–7   : uint64 time_stamp
    # 8–67  : s_sband_cmn_tm (60 bytes)
    #         - 8  : int32 temp_mcu
    #         - 12 : int32 temp_fpga
    #         - 16 : int32 temp_xcvr
    #         - 20 : double volt_vint
    #         - 28 : double volt_vaux
    #         - 36 : double volt_vbram
    #         - 44 : double volt_vpint
    #         - 52 : double volt_vpaux
    #         - 60 : double volt_vpdro
    #
    # After cmn_tm come rx_tm[2], tx_tm, xmt_tm[2], and a bunch of scalars.
    #
    # We know the exact size of the *tail* we care about:
    #   uint32  Reserved;                4
    #   uint8   on_count;                1
    #   uint8   off_count;               1
    #   uint16  sband_reset_cnt;         2
    #   uint8   state;                   1
    #   uint16  beacon_tx_cnt;           2
    #   uint8   Reserved;                1
    #   uint8   Reserved;                1
    #   uint8   rx_port_value;           1  (we only use bit0)
    #   uint16  Reserved x 9;           18
    #   uint32  Reserved;                4
    #   uint16  Reserved x 3;            6
    #   uint8   sband_eps_mode;          1
    #   uint16  Reserved;                2
    #   uint32  Reserved;                4
    #   uint8   Reserved x 14;          14
    #   uint16  Reserved x 2;            4
    #
    # Tail size = 67 bytes.

    CMN_TM_OFFSET   = 8
    CMN_TM_SIZE     = 60
    MIN_HEAD_BYTES  = 8 + CMN_TM_SIZE  # time_stamp + cmn_tm
    TAIL_BYTES      = 67

    if bytes_per_instance < MIN_HEAD_BYTES:
        print(
            f"[WARN] SBAND_TM_PROP: bytes_per_instance ({bytes_per_instance}) "
            f"< minimum head ({MIN_HEAD_BYTES}); only decoding time_stamp & cmn_tm"
        )

    # unknown_mid_bytes: between cmn_tm and tail section
    unknown_mid_bytes = max(0, bytes_per_instance - (MIN_HEAD_BYTES + TAIL_BYTES))

    segments = []

    for idx in range(instance_count):
        inst_start_hex = payload_start_hex + idx * bytes_per_instance * 2
        inst_end_hex   = inst_start_hex + bytes_per_instance * 2

        if inst_end_hex > len(hex_str):
            print(
                f"[WARN] SBAND_TM_PROP: instance {idx} truncated "
                f"(expected up to index {inst_end_hex}, len={len(hex_str)}). Stopping."
            )
            break

        # All byte offsets below are relative to this instance
        inst_hex = hex_str[inst_start_hex:inst_end_hex]

        seg = {
            "Submodule_ID":       submodule_id,
            "Queue_ID":           queue_id,
            "Instance_Index":     idx,
            "Number_of_Instances": instance_count,
        }

        # 1) time_stamp (uint64)
        ts_raw = _read_u64_at(inst_hex, 0)
        seg["Time_Stamp_Raw"] = ts_raw
        try:
            seg["Time_Stamp_Human"] = datetime.utcfromtimestamp(ts_raw) \
                                          .strftime("%Y-%m-%d %H:%M:%S")
        except (OverflowError, OSError, ValueError):
            seg["Time_Stamp_Human"] = None

        # 2) s_sband_cmn_tm (temps & voltages)
        seg["Temp_MCU"]   = _read_i32_at(inst_hex, CMN_TM_OFFSET + 0)
        seg["Temp_FPGA"]  = _read_i32_at(inst_hex, CMN_TM_OFFSET + 4)
        seg["Temp_XCVR"]  = _read_i32_at(inst_hex, CMN_TM_OFFSET + 8)

        seg["Volt_VINT"]  = _read_f64_at(inst_hex, CMN_TM_OFFSET + 12)
        seg["Volt_VAUX"]  = _read_f64_at(inst_hex, CMN_TM_OFFSET + 20)
        seg["Volt_VBRAM"] = _read_f64_at(inst_hex, CMN_TM_OFFSET + 28)
        seg["Volt_VPINT"] = _read_f64_at(inst_hex, CMN_TM_OFFSET + 36)
        seg["Volt_VPAUX"] = _read_f64_at(inst_hex, CMN_TM_OFFSET + 44)
        seg["Volt_VPDRO"] = _read_f64_at(inst_hex, CMN_TM_OFFSET + 52)

        # 3) Middle (rx_tm[2], tx_tm, xmt_tm[2] & some reserved) as raw hex
        #    This is everything between the end of cmn_tm and the start of the tail.
        middle_start_byte = MIN_HEAD_BYTES
        middle_end_byte   = MIN_HEAD_BYTES + unknown_mid_bytes
        seg["Middle_Block_Raw_Hex"] = inst_hex[middle_start_byte*2:middle_end_byte*2]

        # 4) Tail fields (if we have enough bytes)
        if bytes_per_instance >= MIN_HEAD_BYTES + TAIL_BYTES:
            tail_start_byte = MIN_HEAD_BYTES + unknown_mid_bytes
            b = tail_start_byte  # walker in bytes

            # uint32 Reserved
            seg["Tail_Reserved0"] = _read_u32_at(inst_hex, b); b += 4

            seg["On_Count"]         = _read_u8_at(inst_hex, b); b += 1
            seg["Off_Count"]        = _read_u8_at(inst_hex, b); b += 1
            seg["SBand_Reset_Count"] = _read_u16_at(inst_hex, b); b += 2
            seg["State"]            = _read_u8_at(inst_hex, b); b += 1
            seg["Beacon_Tx_Count"]  = _read_u16_at(inst_hex, b); b += 2

            # two reserved u8
            seg["Tail_Reserved1"]   = _read_u8_at(inst_hex, b); b += 1
            seg["Tail_Reserved2"]   = _read_u8_at(inst_hex, b); b += 1

            # rx_port_value (bit0 of this byte)
            rx_port_raw             = _read_u8_at(inst_hex, b); b += 1
            seg["RX_Port_Raw"]      = rx_port_raw
            seg["RX_Port_Value"]    = bool(rx_port_raw & 0x01)

            # 9 * uint16 Reserved
            reserved_16 = []
            for _ in range(9):
                reserved_16.append(_read_u16_at(inst_hex, b))
                b += 2
            seg["Tail_Reserved16_Block1"] = reserved_16

            # uint32 Reserved
            seg["Tail_Reserved3"] = _read_u32_at(inst_hex, b); b += 4

            # 3 * uint16 Reserved
            reserved_16_2 = []
            for _ in range(3):
                reserved_16_2.append(_read_u16_at(inst_hex, b))
                b += 2
            seg["Tail_Reserved16_Block2"] = reserved_16_2

            # sband_eps_mode (uint8)
            seg["SBand_EPS_Mode"] = _read_u8_at(inst_hex, b); b += 1

            # uint16 Reserved
            seg["Tail_Reserved4"] = _read_u16_at(inst_hex, b); b += 2

            # uint32 Reserved
            seg["Tail_Reserved5"] = _read_u32_at(inst_hex, b); b += 4

            # 14 * uint8 Reserved
            reserved_8_block = []
            for _ in range(14):
                reserved_8_block.append(_read_u8_at(inst_hex, b))
                b += 1
            seg["Tail_Reserved8_Block"] = reserved_8_block

            # final 2 * uint16 Reserved
            seg["Tail_Reserved6"] = _read_u16_at(inst_hex, b); b += 2
            seg["Tail_Reserved7"] = _read_u16_at(inst_hex, b); b += 2

        segments.append(seg)

    return segments
