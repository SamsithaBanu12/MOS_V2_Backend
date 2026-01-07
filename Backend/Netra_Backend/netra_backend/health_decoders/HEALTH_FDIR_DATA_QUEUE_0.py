import struct
from datetime import datetime

# ---------------- ENUM TABLES ---------------- #

RM_HW_STATE = {
    0: "RM_HW_POWERED_OFF",
    1: "RM_HW_BOOTING_FAILED",
    2: "RM_HW_POWERED_ON",
    3: "RM_HW_ACTIVE",
    4: "RM_HW_FAILED",
    5: "RM_HW_RECOVERY",
    6: "RM_HW_CORE_BOARD_PWR_SENS",
    7: "RM_HW_MAX_STATE",
}

SENSOR_INTERFACE = {
    0:  "RM_HW_GPS",
    1:  "RM_HW_SBAND",
    2:  "RM_HW_XBAND1",
    3:  "RM_HW_XBAND2",
    4:  "RM_HW_UHF",
    5:  "RM_HW_ADCS",
    6:  "RM_HW_THRU",
    7:  "RM_HW_EPS",
    8:  "RM_HW_PS",
    9:  "RM_HW_ES",
    10: "RM_HW_PS_SSD",
    11: "RM_HW_ES_SSD",
    12: "RM_HW_ETH_NW_SW",
    13: "RM_HW_EEPROM",
    14: "RM_HW_OBC",
    15: "RM_HW_MAX",
}

FDIR_EVENT = {
     0: "FDIR_LOGGER_PWR_ON_STS",
     1: "FDIR_LOGGER_PWR_OFF_STS",
     2: "FDIR_LOGGER_PWR_ON_REQ",
     3: "FDIR_LOGGER_PWR_OFF_REQ",
     4: "FDIR_LOGGER_PWR_RSTR_REQ",
     5: "FDIR_LOGGER_PWR_ON_OFF_RSTR_RDNT_SWTH_ACTV_LIST_RSP",
     6: "FDIR_LOGGER_COMM_CHK_REQ",
     7: "FDIR_LOGGER_COMM_CHK_RSP",
     8: "FDIR_LOGGER_RDNT_SW_REQ",
     9: "FDIR_LOGGER_ACTV_LIST_REQ",
    10: "FDIR_LOGGER_POWERED_ON",
    11: "FDIR_LOGGER_RECV_SEQ_START",
    12: "FDIR_LOGGER_RECV_SEQ_END",
    13: "FDIR_LOGGER_RECV_INTL_IPC",
    14: "FDIR_LOGGER_SEQ_FOUR_NO_RDNT",
    15: "FDIR_LOGGER_SEQ_FOUR_RDNT_SWITCHED",
    16: "FDIR_LOGGER_GPS_OR_PS_OR_ES_SWAPPED",
    17: "FDIR_LOGGER_ERR_RECOVERED",
    18: "FDIR_LOGGER_ERR_SUB_SYSTEM_FAILED",
    19: "FDIR_LOGGER_TMR_EXP",
    20: "FDIR_LOGGER_TMR_STOPPED",
    21: "FDIR_LOGGER_COMM_CHK_RSP_SUCCESS",
    22: "FDIR_LOGGER_COMM_CHK_RSP_FAIL",
    23: "FDIR_LOGGER_BOOT_ERR",
    24: "FDIR_LOGGER_TMR_STARTED",
    25: "FDIR_LOGGER_RESET",
    26: "FDIR_LOGGER_INTF_ERR_REQ",
    27: "FDIR_OBC1_PWR_ON",
    28: "FDIR_OBC2_PWR_ON",
}

# --------- FDIR_MAX_LOG_ENRTY: set from your C config ---------
# Manual says "/// < FDIR_MAX_LOG_ENRTY (1024 * 2)" so max is 2048.
# Use your actual #define value here:
FDIR_MAX_LOG_ENRTY = 8   # TODO: replace 8 with real FDIR_MAX_LOG_ENRTY


def _get_bits(value: int, start: int, length: int) -> int:
    mask = (1 << length) - 1
    return (value >> start) & mask


def _parse_fdir_log_entry_raw(raw: int) -> dict:
    """
    Parse a single 32-bit s_fdir_hm_log_etry_t from its raw uint32 value.
    """
    time_sync        = _get_bits(raw, 0, 1)
    is_rcvy          = _get_bits(raw, 1, 1)
    sub_syst_id      = _get_bits(raw, 2, 5)
    seq_no_or_hw_ste = _get_bits(raw, 7, 3)
    evnt_or_rtry_cnt = _get_bits(raw, 10, 5)
    delta_time       = _get_bits(raw, 15, 15)
    scale            = _get_bits(raw, 30, 2)

    return {
        "raw": raw,

        "time_sync":        time_sync,
        "is_rcvy":          is_rcvy,
        "sub_syst_id":      sub_syst_id,
        "seq_no_or_hw_ste": seq_no_or_hw_ste,
        "evnt_or_rtry_cnt": evnt_or_rtry_cnt,
        "delta_time":       delta_time,
        "scale":            scale,

        # Human-readable interpretations
        "sub_syst_id_str":      SENSOR_INTERFACE.get(sub_syst_id, "UNKNOWN"),
        "seq_no_or_hw_ste_str": RM_HW_STATE.get(seq_no_or_hw_ste, "UNKNOWN"),
        "event_str":            FDIR_EVENT.get(evnt_or_rtry_cnt, "UNKNOWN"),
    }


def HEALTH_FDIR_DATA_QUEUE_0(hex_str: str):
    """
    Parse TM Get Health – FDIR_DATA_QUEUE_ID (QUEUE_ID = 0).

    Header layout (same pattern as your other health functions):
      0   : Submodule ID (1 byte)
      1   : Queue ID    (1 byte)
      2-3 : Number of instance (uint16)
      rest: payload

    Payload per instance is s_fdir_hm_etrs_t:

        typedef struct __attribute__((__packed__))
        {
            s_fdir_hm_log_etry_t entries[FDIR_MAX_LOG_ENRTY]; // each 4 bytes
            uint16_t write_index;                             // 2 bytes
            uint64_t epoch_time_in_ms;                        // 8 bytes
        } s_fdir_hm_etrs_t;
    """

    header_skip_len = 29  # metadata header in bytes

    # TC length (for completeness, same pattern as your other functions)
    tc_len = struct.unpack('<H', bytes.fromhex(hex_str[46:50]))[0]
    tm_len = tc_len * 2 - 8  # you don't use it later, but keeping for consistency

    # Submodule ID and Queue ID
    submodule_id = int(hex_str[50:52], 16)
    queue_id     = int(hex_str[52:54], 16)

    # Number of instances (at (header_skip_len - 2) bytes)
    count_offset = (header_skip_len - 2) * 2
    count = struct.unpack('<H', bytes.fromhex(hex_str[count_offset:count_offset + 4]))[0]

    if count == 0:
        print("[WARN] FDIR (Queue 0) instance count is zero. Skipping parsing.")
        return []

    segments = []

    # size of ONE s_fdir_hm_etrs_t in bytes and hex chars
    struct_bytes_per_instance = 4 * FDIR_MAX_LOG_ENRTY + 2 + 8   # entries + write_index + epoch
    segment_len = struct_bytes_per_instance * 2                   # hex chars per instance

    # Payload starts at byte offset 30 -> hex offset 60
    data_payload = hex_str[60:60 + count * segment_len]

    for idx in range(count):
        seg_hex = data_payload[idx * segment_len:(idx + 1) * segment_len]
        if len(seg_hex) < segment_len:
            continue

        seg_bytes = bytes.fromhex(seg_hex)
        offset = 0

        # ---------- entries[FDIR_MAX_LOG_ENRTY] ----------
        entries = []
        for e_idx in range(FDIR_MAX_LOG_ENRTY):
            raw_val = struct.unpack_from('<I', seg_bytes, offset)[0]  # uint32_t
            offset += 4

            parsed_entry = _parse_fdir_log_entry_raw(raw_val)
            parsed_entry["Entry_Index"] = e_idx
            entries.append(parsed_entry)

        # ---------- write_index (uint16_t) ----------
        write_index = struct.unpack_from('<H', seg_bytes, offset)[0]
        offset += 2

        # ---------- epoch_time_in_ms (uint64_t) ----------
        epoch_time_in_ms = struct.unpack_from('<Q', seg_bytes, offset)[0]
        offset += 8

        # human-readable UTC time
        epoch_time_utc = datetime.utcfromtimestamp(epoch_time_in_ms / 1000.0).strftime(
            '%Y-%m-%d %H:%M:%S'
        )

        segments.append({
            'Submodule_ID':        submodule_id,
            'Queue_ID':            queue_id,
            'Number of Instances': count,
            'Instance_Index':      idx,

            'write_index':         write_index,
            'epoch_time_in_ms':    epoch_time_in_ms,
            'epoch_time_utc':      epoch_time_utc,

            # full log entries array
            'entries':             entries,
        })

    return segments
