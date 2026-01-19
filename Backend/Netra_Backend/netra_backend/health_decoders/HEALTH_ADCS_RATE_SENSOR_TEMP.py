import struct
from datetime import datetime, timezone

def HEALTH_ADCS_RATE_SENSOR_TEMP(hex_str):
    # 1. Skip common metadata header (26 bytes)
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
            # Layout: Operation Status (B), Epoch Time (I), Temperature X (h), Y (h), Z (h)
            # '<B I h h h' = 1 + 4 + 2 + 2 + 2 = 11 bytes
            op_status, epoch_ti, temp_x, temp_y, temp_z = struct.unpack('<BIhhh', bytes.fromhex(seg))
            
            # Convert epoch integer to human-readable format
            # Using timezone-aware objects to represent datetimes in UTC
            timestamp_human = datetime.fromtimestamp(epoch_ti, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            
            segments.append({
                'Submodule_ID': submodule_id,
                'Queue_ID': queue_id,
                'Number of Instances': count,
                'Operation_Status': op_status,
                'Epoch_Time_Human': timestamp_human,
                'Rate_Sensor_Temperature_X': temp_x,
                'Rate_Sensor_Temperature_Y': temp_y,
                'Rate_Sensor_Temperature_Z': temp_z,
            })
        except Exception as e:
            print(f"[ERROR] Failed parsing ADCS_RATE_SENSOR_TEMP segment {idx}: {e}")
            continue
            
    return segments

if __name__ == "__main__":
    hex_string = "8c c5 7a 00 a5 aa f0 a2 c2 60 69 15 00 00 00 81 00 04 6d 02 01 01 ff ff 5c 00 01 05 08 00 00 df c2 60 69 00 00 00 00 00 00 00 ea c2 60 69 00 00 00 00 00 00 00 f4 c2 60 69 00 00 00 00 00 00 00 01 c3 60 69 00 00 00 00 00 00 00 0b c3 60 69 00 00 00 00 00 00 00 16 c3 60 69 00 00 00 00 00 00 00 20 c3 60 69 00 00 00 00 00 00 00 2a c3 60 69 00 00 00 00 00 00 d5 86 06 ee 0d 49 2f 5a ae e1 18 ac 05 e6 83 0d cb 90 a5 a3 5e 5d 52 50 29 82 3a 4b 9d fd 4e bd 44 ba"
    # Note: The test hex string provided by the user has Queue ID 0x10 (16), 
    # but the logic remains the same for Queue ID 0x05.
    print(HEALTH_ADCS_RATE_SENSOR_TEMP(hex_string.replace(" ", "")))