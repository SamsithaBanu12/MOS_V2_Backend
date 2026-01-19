import struct
from datetime import datetime

def HEALTH_ADCS_POS_ERR(hex_str):
    # 1. Skip metadata header (26 bytes)
    header_skip_bytes = 26
    header_skip_chars = header_skip_bytes * 2
    
    if len(hex_str) < (header_skip_chars + 8):
        print(f"[ERROR] Insufficient data length: {len(hex_str)}")
        return []

    # 2. Decoding metadata
    # Submodule ID: byte 26
    submodule_id = int(hex_str[header_skip_chars : header_skip_chars+2], 16)
    
    # Queue ID: byte 27
    queue_id = int(hex_str[header_skip_chars+2 : header_skip_chars+4], 16)
    
    # Number of instances: 2 bytes (UINT16) at bytes 28-29
    count_hex = hex_str[header_skip_chars+4 : header_skip_chars+8]
    count = struct.unpack('<H', bytes.fromhex(count_hex))[0]
    
    if count == 0:
        print(f"[WARN] Sensor count is zero (Parsed from hex: {count_hex}). Skipping parsing.")
        return []

    # 3. Data payload starts at byte 30
    data_start_idx = header_skip_chars + 8
    data_payload = hex_str[data_start_idx:]
    
    # Segment Length = 11 bytes = 22 hex chars
    segment_len_bytes = 11
    segment_len_chars = segment_len_bytes * 2
    
    segments = []
    for idx in range(count):
        start = idx * segment_len_chars
        end = start + segment_len_chars
        seg = data_payload[start:end]
        
        if len(seg) < segment_len_chars:
            break
            
        try:
            # Layout (Table 63): Operation Status (B), Epoch Time (I), X_Err (h), Y_Err (h), Z_Err (h)
            # '<B I h h h' = 1 + 4 + 2 + 2 + 2 = 11 bytes
            op_status, epoch_ti, raw_x, raw_y, raw_z = struct.unpack('<BIhhh', bytes.fromhex(seg))
            
            # Position Error = RAWVAL * 0.01
            pos_x_err = raw_x * 0.01
            pos_y_err = raw_y * 0.01
            pos_z_err = raw_z * 0.01
            
            # Convert epoch integer to human-readable format
            timestamp_human = datetime.utcfromtimestamp(epoch_ti).strftime('%Y-%m-%d %H:%M:%S')
            
            segments.append({
                'Submodule_ID': submodule_id,
                'Queue_ID': queue_id,
                'Number of Instances': count,
                'Operation_Status': op_status,
                'Epoch_Time_Human': timestamp_human,
                'Position_X_Error': pos_x_err,
                'Position_Y_Error': pos_y_err,
                'Position_Z_Error': pos_z_err,
            })
        except Exception as e:
            print(f"[ERROR] Failed parsing ADCS_POS_ERR segment {idx}: {e}")
            continue
            
    return segments

if __name__ == "__main__":
    hex_string = "8c c5 7b 00 a5 aa f0 a2 c2 60 69 23 00 00 00 81 00 04 6d 02 01 01 ff ff 5c 00 01 1b 08 00 00 df c2 60 69 00 00 00 00 00 00 00 ea c2 60 69 00 00 00 00 00 00 00 f4 c2 60 69 00 00 00 00 00 00 00 01 c3 60 69 00 00 00 00 00 00 00 0b c3 60 69 00 00 00 00 00 00 00 16 c3 60 69 00 00 00 00 00 00 00 20 c3 60 69 00 00 00 00 00 00 00 2a c3 60 69 00 00 00 00 00 00 10 9d dd b1 25 48 95 fd 26 ad 5f 88 0a a6 b4 a1 3a b8 45 f7 6b 27 97 68 05 04 b2 26 3c c1 29 29 b2 ba"
    print(HEALTH_ADCS_POS_ERR(hex_string.replace(" ", "")))