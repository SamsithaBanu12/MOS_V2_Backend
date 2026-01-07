import struct
from datetime import datetime

def HEALTH_GNSS_DATA(hex_str: str):
    """
    Parse TM Get Health – GNSS_DATA_QUEUE_ID (QueueID = 0).

    Per instance struct (ahal_gps_health_info) decoded as:

        gps_time_stamp hwm_time;    // year, month, day, hour, min, millisec
        uint8_t reserv;
        uint8_t clk_model_recv_sts;
        uint8_t utc_known_recv_sts;
        uint8_t pos_sts;
        uint8_t lna_fail_recv_sts;
        uint8_t cpu_overload_recv_sts;
        uint8_t antna_gain_state;
        uint8_t compo_hw_fail_sts;
        float antenna_curr;
        float antenna_volt;
        float receiver_volt;
        float temperature;
    """

    header_skip_len = 29  # metadata header in bytes (same convention as your other functions)

    # TC length (for completeness)
    tc_len = struct.unpack('<H', bytes.fromhex(hex_str[46:50]))[0]
    tm_len = tc_len * 2 - 8  # not used further, but kept for consistency

    # Submodule ID & Queue ID (standard positions in your other parsers)
    submodule_id = int(hex_str[50:52], 16)
    queue_id     = int(hex_str[52:54], 16)

    # Number of instances: UINT16 at (header_skip_len - 2) bytes
    count_offset = (header_skip_len - 2) * 2
    count = struct.unpack('<H', bytes.fromhex(hex_str[count_offset:count_offset + 4]))[0]

    if count == 0:
        print("[WARN] GNSS instance count is zero. Skipping parsing.")
        return []

    segments = []

    # One ahal_gps_health_info is 32 bytes => 64 hex chars
    segment_len = 64  # in hex characters

    # Payload starts at hex_str[60:], same pattern as your other queue functions
    data_payload = hex_str[60:60 + count * segment_len]

    for idx in range(count):
        seg = data_payload[idx * segment_len:(idx + 1) * segment_len]
        if len(seg) < segment_len:
            continue

        offset = 0

        # -------- gps_time_stamp (8 bytes = 16 hex) --------
        year      = struct.unpack('<H', bytes.fromhex(seg[offset:offset + 4]))[0]
        offset   += 4

        month     = int(seg[offset:offset + 2], 16); offset += 2
        day       = int(seg[offset:offset + 2], 16); offset += 2
        hour      = int(seg[offset:offset + 2], 16); offset += 2
        minute    = int(seg[offset:offset + 2], 16); offset += 2

        millisec  = struct.unpack('<H', bytes.fromhex(seg[offset:offset + 4]))[0]
        offset   += 4

        # Human-readable UTC time (assume seconds = 0, millisec -> microseconds)
        try:
            gnss_time = datetime(
                year=year,
                month=month,
                day=day,
                hour=hour,
                minute=minute,
                second=0,
                microsecond=millisec * 1000,
            )
            gnss_time_str = gnss_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # keep millis
        except ValueError:
            gnss_time = None
            gnss_time_str = "INVALID_DATETIME"

        # -------- ahal_gps_rx_sts_hm (8 x uint8 = 16 hex) --------
        reserv               = int(seg[offset:offset + 2], 16); offset += 2
        clk_model_recv_sts   = int(seg[offset:offset + 2], 16); offset += 2
        utc_known_recv_sts   = int(seg[offset:offset + 2], 16); offset += 2
        pos_sts              = int(seg[offset:offset + 2], 16); offset += 2
        lna_fail_recv_sts    = int(seg[offset:offset + 2], 16); offset += 2
        cpu_overload_recv_sts = int(seg[offset:offset + 2], 16); offset += 2
        antna_gain_state     = int(seg[offset:offset + 2], 16); offset += 2
        compo_hw_fail_sts    = int(seg[offset:offset + 2], 16); offset += 2

        # Optional human-readable interpretations (0 = OK, 1 = problem, per your text)
        clk_model_recv_sts_str = "Clock model status VALID"   if clk_model_recv_sts == 0 else "Clock model status INVALID"
        utc_known_recv_sts_str = "UTC time VALID"             if utc_known_recv_sts == 0 else "UTC time INVALID"
        pos_sts_str            = "GNSS position VALID"        if pos_sts == 0 else "GNSS position INVALID"

        # -------- floats (4 x float = 16 bytes = 32 hex) --------
        antenna_curr   = struct.unpack('<f', bytes.fromhex(seg[offset:offset + 8]))[0]
        offset        += 8

        antenna_volt   = struct.unpack('<f', bytes.fromhex(seg[offset:offset + 8]))[0]
        offset        += 8

        receiver_volt  = struct.unpack('<f', bytes.fromhex(seg[offset:offset + 8]))[0]
        offset        += 8

        temperature    = struct.unpack('<f', bytes.fromhex(seg[offset:offset + 8]))[0]
        offset        += 8

        segments.append({
            # TM framing
            'Submodule_ID':        submodule_id,
            'Queue_ID':            queue_id,
            'Number_of_Instances': count,
            'Instance_Index':      idx,

            # Time
            'Year':        year,
            'Month':       month,
            'Day':         day,
            'Hour':        hour,
            'Minute':      minute,
            'Millisec':    millisec,
            'GNSS_Time_UTC': gnss_time_str,

            # Receiver status
            'reserv':                reserv,
            'clk_model_recv_sts':    clk_model_recv_sts,
            'clk_model_recv_sts_str': clk_model_recv_sts_str,
            'utc_known_recv_sts':    utc_known_recv_sts,
            'utc_known_recv_sts_str': utc_known_recv_sts_str,
            'pos_sts':               pos_sts,
            'pos_sts_str':           pos_sts_str,
            'lna_fail_recv_sts':     lna_fail_recv_sts,
            'cpu_overload_recv_sts': cpu_overload_recv_sts,
            'antna_gain_state':      antna_gain_state,
            'compo_hw_fail_sts':     compo_hw_fail_sts,

            # Power / health
            'antenna_curr':   antenna_curr,
            'antenna_volt':   antenna_volt,
            'receiver_volt':  receiver_volt,
            'temperature':    temperature,
        })

    return segments
