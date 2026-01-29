import struct
from datetime import datetime

def HEALTH_ADCS_QUAT_ERR_VEC(hex_str):
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
            # Layout: Operation Status (B), Epoch Time (I), Q1 (h), Q2 (h), Q3 (h)
            # '<B I h h h' = 1 + 4 + 2 + 2 + 2 = 11 bytes
            op_status, epoch_ti, raw_q1, raw_q2, raw_q3 = struct.unpack('<BIhhh', bytes.fromhex(seg))
            
            # Scale = 0.01
            quat_q1 = raw_q1 * 0.01
            quat_q2 = raw_q2 * 0.01
            quat_q3 = raw_q3 * 0.01
            
            # Convert epoch integer to human-readable format
            timestamp = datetime.utcfromtimestamp(epoch_ti).strftime('%Y-%m-%d %H:%M:%S')
            
            segments.append({
                'Submodule_ID': submodule_id,
                'Queue_ID': queue_id,
                'Number of Instances': count,
                'Operation_Status': op_status,
                'Epoch_Time_Human': timestamp,
                'Quaternion Error Q1': quat_q1,
                'Quaternion Error Q2': quat_q2,
                'Quaternion Error Q3': quat_q3,
            })
        except Exception as e:
            print(f"[ERROR] Failed parsing ADCS_QUAT_ERR_VEC segment {idx}: {e}")
            continue
            
    return segments
