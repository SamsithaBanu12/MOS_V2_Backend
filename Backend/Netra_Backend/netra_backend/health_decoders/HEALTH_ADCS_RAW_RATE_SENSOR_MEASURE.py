import struct 
from datetime import datetime, timezone

def HEALTH_ADCS_RAW_RATE_SENSOR_MEASURE(hex_str):
    # 1. Skip metadata header (26 bytes)
    header_skip_bytes = 26
    header_skip_chars = header_skip_bytes * 2
    
    if len(hex_str) < (header_skip_chars + 8):
        print(f"[ERROR] Insufficient data length: {len(hex_str)}")
        return []

    # 2. Decoding QM metadata
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
    
    # Segment Length = 11 bytes = 22 hex chars (Table 44)
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
            # Layout (Table 44): Operation Status (B), Epoch Time (I), X (h), Y (h), Z (h)
            # '<B I h h h' = 1 + 4 + 2 + 2 + 2 = 11 bytes
            op_status, epoch_ti, raw_rate_x, raw_rate_y, raw_rate_z = struct.unpack('<BIhhh', bytes.fromhex(seg))
            
            # Convert epoch integer to human-readable format (UTC)
            timestamp_human = datetime.fromtimestamp(epoch_ti, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            
            segments.append({
                'Submodule_ID': submodule_id,
                'Queue_ID': queue_id,
                'Number of Instances': count,
                'Operation_Status': op_status,
                'Epoch_Time_Human': timestamp_human,
                'Raw_Rate_Sensor_X': raw_rate_x,
                'Raw_Rate_Sensor_Y': raw_rate_y,
                'Raw_Rate_Sensor_Z': raw_rate_z,
            })
        except Exception as e:
            print(f"[ERROR] Failed parsing ADCS_RAW_RATE_SENSOR_MEASURE segment {idx}: {e}")
            continue
            
    return segments

if __name__ == "__main__":
    # Test with similar hex string if available. 
    # Example snippet using known metadata:
    hex_string = "8c c5 75 00 a5 aa f0 a2 c2 60 69 10 00 00 00 81 00 04 6d 02 01 01 ff ff 5c 00 01 11 08 00 00 df c2 60 69 00 00 d9 ff 01 00 00 ea c2 60 69 00 00 d9 ff 01 00 00 f4 c2 60 69 00 00 d9 ff 01 00 00 01 c3 60 69 01 00 d9 ff 01 00 00 0b c3 60 69 01 00 d9 ff 01 00 00 16 c3 60 69 01 00 d9 ff 01 00 00 20 c3 60 69 01 00 d9 ff 01 00 00 2a c3 60 69 02 00 d9 ff 01 00"
    print(HEALTH_ADCS_RAW_RATE_SENSOR_MEASURE(hex_string.replace(" ", "")))
