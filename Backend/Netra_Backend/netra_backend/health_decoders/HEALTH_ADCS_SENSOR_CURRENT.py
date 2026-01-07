import struct
from datetime import datetime


def HEALTH_ADCS_SENSOR_CURRENT(hex_str):
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

    segment_len = 26
    data_payload = hex_str[60:60+count * segment_len]
    segments = []
    for idx in range(count):
        seg = data_payload[idx * segment_len:(idx + 1) * segment_len]
        if len(seg) < segment_len:
           continue
        operation_status = int(seg[0:2], 16)
        epoch_bytes = bytes.fromhex(seg[2:10])
        epoch_time = struct.unpack('<I', epoch_bytes)[0]
        epoch_time_human = datetime.utcfromtimestamp(epoch_time) \
                                .strftime('%Y-%m-%d %H:%M:%S')
        nadir_sensor_3v3_current = struct.unpack('<H', bytes.fromhex(seg[10:14]))[0] * 0.1
        fss_3v3_current = struct.unpack('<H', bytes.fromhex(seg[14:18]))[0] * 0.1
        nadir_sram_current = struct.unpack('<H', bytes.fromhex(seg[18:22]))[0] * 0.1
        fss_sram_current = struct.unpack('<H', bytes.fromhex(seg[22:26]))[0] * 0.1

        segments.append({
            'Submodule_ID':           submodule_id,
            'Queue_ID':               queue_id,
            'Number of Instances':    count,
            'Operation_Status':       operation_status,
            'Epoch_Time_Human':       epoch_time_human,
            'Nadir_Sensor_3V3_Current': nadir_sensor_3v3_current,
            'FSS_3V3_Current':        fss_3v3_current,  
            'Nadir_SRAM_Current':     nadir_sram_current,
            'FSS_SRAM_Current':       fss_sram_current,
        })
    return segments