import struct
from datetime import datetime
def HEALTH_SENSORS_TEMP_SPW02_DATA(hex_str):
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
    segment_len=16

    segment_len1=segment_len
    data_payload = hex_str[60:60+count * segment_len1]

    segments = []
    for idx in range(count):

        seg = data_payload[idx * segment_len1:(idx + 1) * segment_len1]
        if len(seg) < segment_len1:
           continue
        offset = 0
        temperature=struct.unpack('<f', bytes.fromhex(seg[offset:offset+8]))[0]
        offset += 8
        temp_epoch_time=seg[offset:offset+8]
        offset += 8
        temp_reversed=''.join([temp_epoch_time[i:i + 2] for i in range(0, 8, 2)][::-1])
        
        temp_epoch_time=int(temp_reversed,16)
        temp_epoch_readable= datetime.utcfromtimestamp(temp_epoch_time).strftime('%Y-%m-%d %H:%M:%S')
        
        segments.append({
            'Submodule_ID': submodule_id,
            'Queue_ID': queue_id,
            'Number of Instances': count,
            'temperature': temperature,
            'temp_epoch_time':temp_epoch_readable})

    return segments