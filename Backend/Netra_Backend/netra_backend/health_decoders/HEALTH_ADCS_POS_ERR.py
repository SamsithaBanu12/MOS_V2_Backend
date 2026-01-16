import struct
from datetime import datetime

def HEALTH_ADCS_POS_ERR(hex_str):
    header_skip_len = 29  # metadata header in bytes
    tc_len = struct.unpack('<H', bytes.fromhex(hex_str[46:50]))[0]
    tm_len = tc_len * 2 - 8
    submodule_id = int(hex_str[50:52], 16)
    queue_id = int(hex_str[52:54], 16)
    count_offset = (header_skip_len - 2) * 2

    count = struct.unpack('<H', bytes.fromhex(hex_str[count_offset:count_offset + 4]))[0]
    if count == 0:
        print("[WARN] Sensor count is zero. Skipping parsing.")
        return []

    segment_len_bytes = 11
    segment_len_hex = segment_len_bytes * 2
    
    # Payload usually starts at index 60 in these hex strings (byte offset 30)
    data_payload = hex_str[60:60 + count * segment_len_hex]

    segments = []
    for idx in range(count):
        seg = data_payload[idx * segment_len_hex:(idx + 1) * segment_len_hex]
        if len(seg) < segment_len_hex:
            continue
        
        try:
            # Layout: Operation Status (B), Epoch Time (I), X_Err (h), Y_Err (h), Z_Err (h)
            # '<B I h h h' = 1 + 4 + 2 + 2 + 2 = 11 bytes
            op_status, epoch_ti, raw_x, raw_y, raw_z = struct.unpack('<BIhhh', bytes.fromhex(seg))
            
            # Position Error = RAWVAL * 0.01
            pos_x_err = raw_x * 0.01
            pos_y_err = raw_y * 0.01
            pos_z_err = raw_z * 0.01
            
            # Convert epoch integer to human-readable format
            timestamp = datetime.utcfromtimestamp(epoch_ti).strftime('%Y-%m-%d %H:%M:%S')
            
        except Exception as e:
            print(f"Error unpacking ADCS_POS_ERR data segment {idx}: {e}")
            continue

        segments.append({
            'Submodule_ID': submodule_id,
            'Queue_ID': queue_id,
            'Number of Instances': count,
            'Operation_Status': op_status,
            'Timestamp': timestamp,
            'Position_X_Error': pos_x_err,
            'Position_Y_Error': pos_y_err,
            'Position_Z_Error': pos_z_err,
        })
    return segments
