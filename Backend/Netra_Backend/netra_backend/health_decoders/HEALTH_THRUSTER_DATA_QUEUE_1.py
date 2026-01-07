import struct

# ---------------- ENUM TABLES ---------------- #

CURRENT_EVENT_ENUM = {
    1:    'PRPLSN_TANK_TH_CTDNG_TMR_EXPRY',
    2:    'PRPLSN_HM_PRDCTY_TMR_EXPRY',
    9000: 'PRPLSN_PWR_ON_NTF',
    9001: 'PRPLSN_PWR_OFF_NTF',
    9007: 'PRPLSN_ADCS_ANOMALY_OCCURED',
    9008: 'PRPLSN_OBC_FIRINIG_START_NTFY',
    9010: 'PRPLSN_FIRINIG_STOP_NTFY',
}

FSM_STATE_ENUM = {
    0x0: 'PRPLSN_PWR_OFF_STATE',
    0x1: 'PRPLSN_STANDBY',
    0x2: 'PRPLSN_THRML_CTDNG',
    0x3: 'PRPLSN_FIRING',
    0x4: 'PRPLSN_SAFE',
    0x5: 'PRPLSN_COMSISNG',
}

FSM_ERROR_ENUM = {
    0:  'PRPLSN_NO_ERR',
    5:  'PRPLSN_INVALID_PARAM_ERR',
    6:  'PRPLSN_INVALID_MODE_ERR',
    9:  'PRPLSN_COMM_ERR',
    15: 'PRPLSN_COMISNG_ERR',
    16: 'PRPLSN_NOT_POWERED_ERR',
}

# ------------------------------------------------ #
#   COMPLETE FUNCTION TO PARSE 8-BYTE FSM HM INFO
# ------------------------------------------------ #

def HEALTH_THRUSTER_DATA_QUEUE_1(hex_str):

    header_skip_len = 29  # metadata header in bytes

    # tc_len located at hex_str[46:50] (2 bytes of hex)
    tc_len = struct.unpack('<H', bytes.fromhex(hex_str[46:50]))[0]
    tm_len = tc_len * 2 - 8

    submodule_id = int(hex_str[50:52], 16)
    queue_id = int(hex_str[52:54], 16)

    count_offset = (header_skip_len - 2) * 2  # convert bytes → hex chars offset
    count = struct.unpack('<H', bytes.fromhex(hex_str[count_offset:count_offset + 4]))[0]

    if count == 0:
        print("[WARN] Sensor count is zero. Skipping parsing.")
        return []

    segment_len = 9                        # struct size in bytes
    segment_hex_len = segment_len * 2      # number of hex chars per segment

    # payload starts at byte offset 60 → hex offset 120
    data_payload_hex = hex_str[60:60 + count * segment_hex_len]
    segments = []

    for idx in range(count):

        seg_hex = data_payload_hex[idx * segment_hex_len:(idx + 1) * segment_hex_len]

        if len(seg_hex) < segment_hex_len:
            continue


        seg_bytes = bytes.fromhex(seg_hex)
            # Little-endian packed struct: <BHBI
        current_fsm_state, current_event, fsm_err_sts, state_utc_time = \
        struct.unpack('<BHBI', seg_bytes)



    segments.append({
        "current_fsm_state": current_fsm_state,
        "current_fsm_state_str": FSM_STATE_ENUM.get(current_fsm_state, "Reserved"),

        "current_event": current_event,
        "current_event_str": CURRENT_EVENT_ENUM.get(current_event, "Reserved"),

        "fsm_err_sts": fsm_err_sts,
        "fsm_err_sts_str": FSM_ERROR_ENUM.get(fsm_err_sts, "Reserved"),

        "state_utc_time": state_utc_time
    })
    return segments
