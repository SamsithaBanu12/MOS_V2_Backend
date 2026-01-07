import struct
from datetime import datetime


def HEALTH_ADCS_POS_LLH(hex_str):
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

    segment_len1=22
    data_payload = hex_str[60:60+count * segment_len]

    segments = []
    for idx in range(count):

        seg = data_payload[idx * segment_len1:(idx + 1) * segment_len1]
        if len(seg) < segment_len1:
           continue
     
     
        offset=0
        operation_status = int(seg[offset:offset+2],16)
        offset+=2
        epoch_bytes = bytes.fromhex(seg[offset:offset+8])
        offset+=8
        epoch_time = struct.unpack('<I', epoch_bytes)[0]
        epoch_time_human = datetime.utcfromtimestamp(epoch_time) \
                                .strftime('%Y-%m-%d %H:%M:%S')

        # Longitude (signed short, ×0.01, range: -180 to +180)
        pos_llh_x_raw = struct.unpack('<h', bytes.fromhex(seg[offset:offset+4]))[0]
        offset+=4
        longitude = pos_llh_x_raw * 0.01


        pos_llh_y = struct.unpack('<h', bytes.fromhex(seg[offset:offset+4]))[0] * 0.01
        offset+=4
        pos_llh_z = struct.unpack('<H',  bytes.fromhex(seg[offset:offset+4]))[0] * 0.1
        offset+=4
        segments.append({
            'Submodule_ID':           submodule_id,
            'Queue_ID':               queue_id,
            'Number of Instances':                   count,
            'Operation_Status':       operation_status,
            'Epoch_Time_Human':       epoch_time_human,
            'Geocentric_longitude':            longitude,
            'Geocentric_latitude':              pos_llh_y,
            'Geocentric_altitude':              pos_llh_z
        })
    
    return segments
