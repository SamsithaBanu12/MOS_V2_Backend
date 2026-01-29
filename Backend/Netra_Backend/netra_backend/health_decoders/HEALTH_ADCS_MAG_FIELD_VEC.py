import struct
from datetime import datetime


def HEALTH_ADCS_MAG_FIELD_VEC(hex_str):
    # Standard header is 26 bytes. Payload starts at byte 26.
    # Payload header (Submodule, Queue, NumInstance) is 4 bytes.
    # Total skip to start of segments is 26 + 4 = 30 bytes.
    header_skip_len = 30
    
    # TM_LEN is at bytes 24-25 (indices 48:52)
    tm_len_raw = struct.unpack('<H', bytes.fromhex(hex_str[48:52]))[0]
    # In some implementations, tm_len might need adjustment, but we'll focus on offsets first.
    
    submodule_id = int(hex_str[52:54], 16) # Byte 26
    queue_id = int(hex_str[54:56], 16)     # Byte 27
    
    # count_offset is for NUM_INSTANCE at bytes 28-29 (indices 56:60)
    count_offset = 56
    count = struct.unpack('<H', bytes.fromhex(hex_str[count_offset:count_offset + 4]))[0]
    
    if count == 0:
        print("[WARN] Sensor count is zero. Skipping parsing.")
        return []

    segment_len1 = 22 # 11 bytes per segment
    data_payload = hex_str[60:] # Data starts at byte 30 (index 60)

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
        mag_field_x = struct.unpack('<h', bytes.fromhex(seg[10:14]))[0] * 0.01
        mag_field_y = struct.unpack('<h', bytes.fromhex(seg[14:18]))[0] * 0.01
        mag_field_z = struct.unpack('<h', bytes.fromhex(seg[18:22]))[0] * 0.01
        segments.append({
            'Submodule_ID':           submodule_id,
            'Queue_ID':               queue_id,
            'Number of Instances':                   count,
            'Operation_Status':       operation_status,
            'Epoch_Time_Human':       epoch_time_human,
            'Mag_Field_X':            mag_field_x,
            'Mag_Field_Y':            mag_field_y,
            'Mag_Field_Z':            mag_field_z
        })
    return segments

