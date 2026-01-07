import struct
from datetime import datetime

def HEALTH_ADCS_SAT_POS_ECI_FRAME(hex_str):
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

    segment_len=58

    segment_len1=58
    data_payload = hex_str[60:60+count * segment_len]

    segments = []
    for idx in range(count):

        seg = data_payload[idx * segment_len1:(idx + 1) * segment_len1]
        if len(seg) < segment_len1:
           continue
        operation_status = int(seg[0:2], 16)
        epoch_bytes = bytes.fromhex(seg[2:10])
        epoch_time = struct.unpack('<I', epoch_bytes)[0]
        epoch_time_human = datetime.utcfromtimestamp(epoch_time) \
                                .strftime('%Y-%m-%d %H:%M:%S')
        sat_pos_eci_x = struct.unpack('<d', bytes.fromhex(seg[10:26]))[0] 
        sat_pos_eci_y = struct.unpack('<d', bytes.fromhex(seg[26:42]))[0] 
        sat_pos_eci_z = struct.unpack('<d', bytes.fromhex(seg[42:58]))[0] 
        segments.append({
            'Submodule_ID':           submodule_id,
            'Queue_ID':               queue_id,
            'Number of Instances':                   count,
            'Operation_Status':       operation_status,
            'Epoch_Time_Human':       epoch_time_human,
            'Sat_Pos_ECI_X':          sat_pos_eci_x,
            'Sat_Pos_ECI_Y':          sat_pos_eci_y,
            'Sat_Pos_ECI_Z':          sat_pos_eci_z
        })
    return segments
