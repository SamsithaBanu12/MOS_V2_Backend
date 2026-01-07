import struct
from datetime import datetime

def HEALTH_THRUSTER_DATA_QUEUE_0(hex_str):

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

        # Parse the struct: uint32, uint8, float
        time, tank_on_off_sts, tank_temp = struct.unpack('<IBf', seg_bytes)

        segments.append({
            "TIME": time,
            "TANK_ON_OFF_STATUS": tank_on_off_sts,
            "TANK_TEMP": tank_temp
        })

    return segments
