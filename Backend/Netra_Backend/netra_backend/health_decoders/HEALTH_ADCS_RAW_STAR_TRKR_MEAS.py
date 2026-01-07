import struct
from datetime import datetime


def HEALTH_ADCS_RAW_STAR_TRKR_MEAS(hex_str):
    header_skip_len = 29  # metadata header in bytes
    tc_len=struct.unpack('<H', bytes.fromhex(hex_str[46:50]))[0]
    tm_len=tc_len*2 -8
    submodule_id = int(hex_str[50:52], 16)
    queue_id = int(hex_str[52:54], 16)
    count_offset = (header_skip_len - 2) * 2

    count = struct.unpack('<H', bytes.fromhex(hex_str[count_offset:count_offset + 4]))[0]
    if count == 0:
        print("[WARN] Sensor count is zero. Skipping parsing.")
        return []

    segment_len=tm_len//count

    segment_len1=segment_len
    data_payload = hex_str[60:68-tm_len]
    
    segments = []
    for idx in range(count):

        seg = data_payload[idx * segment_len1:(idx + 1) * segment_len1]
        if len(seg) < segment_len1:
           continue
        operation_status = int(seg[0:2], 16)
        epoch_time = struct.unpack('<I', bytes.fromhex(seg[2:10]))[0]
        epoch_time_human = datetime.utcfromtimestamp(epoch_time) \
                                .strftime('%Y-%m-%d %H:%M:%S')
        
        num_stars_detected = int(seg[10], 16)
        Reserved = int(seg[11:15], 16)
       
        num_star_identified = int(seg[15], 16)
        # Star Tracker identification mode (1 byte, ENUM, Table 39)
        identification_mode_val = int(seg[16], 16)
        identification_mode_enum = {
            0: "ADCS_STAR_MODE_TRACKING",
            1: "ADCS_STAR_MODE_LOST"
        }
        identification_mode = identification_mode_enum.get(identification_mode_val, f"UNKNOWN({identification_mode_val})")
        reserved=seg[17:53]

        segments.append({

            'Submodule_ID': submodule_id,
            'Queue_ID': queue_id,
            'Number of Instances': count,
            'operation_status': operation_status,
            'epoch_time_human': epoch_time_human,
            'num_stars_detected': num_stars_detected,
            'num_star_identified': num_star_identified,
            'identification_mode': identification_mode
        })
    return segments
