
import struct 
from datetime import datetime

def HEALTH_ADCS_EST_RATES(hex_str):
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
    
    # Number of instances: 2 bytes at bytes 28-29
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
            # Table 46: Estimated Angular Rate Structure format (11 bytes)
            # Operation Status: 1 byte
            operation_status = int(seg[0:2], 16)
            
            # Epoch: 4 bytes (UINT32)
            epoch_hex = seg[2:10]
            epoch_time = struct.unpack('<I', bytes.fromhex(epoch_hex))[0]
            epoch_time_human = datetime.utcfromtimestamp(epoch_time).strftime('%Y-%m-%d %H:%M:%S')
            
            # X, Y, Z rates: 2 bytes each (INT16) * 0.01
            est_rate_x = struct.unpack('<h', bytes.fromhex(seg[10:14]))[0] * 0.01
            est_rate_y = struct.unpack('<h', bytes.fromhex(seg[14:18]))[0] * 0.01
            est_rate_z = struct.unpack('<h', bytes.fromhex(seg[18:22]))[0] * 0.01
            
            segments.append({
                'Submodule_ID':         submodule_id,
                'Queue_ID':             queue_id,
                'Number_of_Instances':  count,
                'Operation_Status':     operation_status,
                'Epoch_Time_Human':     epoch_time_human,
                'Est_Rate_X':           est_rate_x,
                'Est_Rate_Y':           est_rate_y,
                'Est_Rate_Z':           est_rate_z
            })
        except Exception as e:
            print(f"[ERROR] Failed parsing segment {idx}: {e}")
            continue
            
    return segments

hex_string = "8c c5 77 00 a5 aa f0 a2 c2 60 69 12 00 00 00 81 00 04 6d 02 01 01 ff ff 5c 00 01 12 08 00 00 df c2 60 69 00 00 d9 ff 01 00 00 ea c2 60 69 00 00 d9 ff 01 00 00 f4 c2 60 69 00 00 d8 ff 01 00 00 01 c3 60 69 01 00 d9 ff 01 00 00 0b c3 60 69 01 00 d8 ff 01 00 00 16 c3 60 69 01 00 d9 ff 01 00 00 20 c3 60 69 01 00 d9 ff 01 00 00 2a c3 60 69 02 00 d9 ff 01 00 a8 72 24 c0 2e 21 7f ce e1 80 a8 a2 de 58 e0 e6 cd 0e e9 4c 89 e4 f0 0d 33 a6  05 fe ae 49 7e 19 c5 ba"
print(HEALTH_ADCS_EST_RATES(hex_string.replace(" ","")))