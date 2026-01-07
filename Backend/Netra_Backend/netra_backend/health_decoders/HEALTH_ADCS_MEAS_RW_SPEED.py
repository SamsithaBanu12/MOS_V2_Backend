import struct
from datetime import datetime


def HEALTH_ADCS_MEAS_RW_SPEED(hex_str):
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

    segment_len1=28
    data_payload = hex_str[60:60+count * segment_len]

    segments = []
    for idx in range(count):

        seg = data_payload[idx * segment_len1:(idx + 1) * segment_len1]
        if len(seg) < segment_len1:
           continue
        operation_status = int(seg[0:2], 16)
        epoch_bytes = bytes.fromhex(seg[2:10])
        epoch_time = struct.unpack('<I', epoch_bytes)[0]
        epoch_time_human = datetime.utcfromtimestamp(epoch_time).strftime('%Y-%m-%d %H:%M:%S')
        num_reaction_wheels = int(seg[10:12], 16)
        
        Command_reaction_wheel1_speed = struct.unpack('<h', bytes.fromhex(seg[12:16]))[0] 
        Command_reaction_wheel2_speed = struct.unpack('<h', bytes.fromhex(seg[16:20]))[0]
        Command_reaction_wheel3_speed = struct.unpack('<h', bytes.fromhex(seg[20:24]))[0] 
        Command_reaction_wheel4_speed = struct.unpack('<h', bytes.fromhex(seg[24:28]))[0]

        segments.append({
            'Submodule_ID':           submodule_id,
            'Queue_ID':               queue_id,
            'Number of Instances':                   count,
            'Operation_Status': operation_status,
            'Epoch_Time_Human': epoch_time_human,
            'Number of reaction wheel': num_reaction_wheels,
            'Command_Wheel_Speed_1': Command_reaction_wheel1_speed,
            'Command_Wheel_Speed_2': Command_reaction_wheel2_speed,
            'Command_Wheel_Speed_3': Command_reaction_wheel3_speed,
            'Command_Wheel_Speed_4': Command_reaction_wheel4_speed
        })
    return segments
