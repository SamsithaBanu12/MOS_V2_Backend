import struct
from datetime import datetime

def HEALTH_ADCS_RAW_FSS_SNS(hex_str):
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

    segment_len=22

    segment_len1=segment_len
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
        raw_fss_sns_x = struct.unpack('<h', bytes.fromhex(seg[10:14]))[0]
        raw_fss_sns_y = struct.unpack('<h', bytes.fromhex(seg[14:18]))[0]
        FSS_CAPTURE_STATUS =int(seg[18:20], 16)
        FSS_result =int(seg[20:22], 16) 
        segments.append({
            'Submodule_ID':           submodule_id,
            'Queue_ID':               queue_id,
            'Number of Instances':                   count,
            'Operation_Status':       operation_status,
            'Epoch_Time_Human':       epoch_time_human,
            'FSS_RAW_X':              raw_fss_sns_x,
            'FSS_RAW_Y':              raw_fss_sns_y,
            'FSS_capture_status':     FSS_CAPTURE_STATUS,
            'fss_capture_result':     FSS_result
        })
    return segments