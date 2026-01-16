
import struct 
from datetime import datetime

def HEALTH_ADCS_MGTRQR_CMD(hex_str):
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
            # Table 59: HM Magnetorquer command telemetry format (11 bytes)
            # Operation Status: 1 byte
            operation_status = int(seg[0:2], 16)
            
            # Epoch: 4 bytes (UINT32)
            epoch_hex = seg[2:10]
            epoch_time = struct.unpack('<I', bytes.fromhex(epoch_hex))[0]
            epoch_time_human = datetime.utcfromtimestamp(epoch_time).strftime('%Y-%m-%d %H:%M:%S')
            
            # X, Y, Z commanded on-time: 2 bytes each (INT16)
            mgtrqr_cmd_x = struct.unpack('<h', bytes.fromhex(seg[10:14]))[0]
            mgtrqr_cmd_y = struct.unpack('<h', bytes.fromhex(seg[14:18]))[0]
            mgtrqr_cmd_z = struct.unpack('<h', bytes.fromhex(seg[18:22]))[0]
            
            segments.append({
                'Submodule_ID':         submodule_id,
                'Queue_ID':             queue_id,
                'Number_of_Instances':  count,
                'Operation_Status':     operation_status,
                'Epoch_Time_Human':     epoch_time_human,
                'MGTRQR_Cmd_X':         mgtrqr_cmd_x,
                'MGTRQR_Cmd_Y':         mgtrqr_cmd_y,
                'MGTRQR_Cmd_Z':         mgtrqr_cmd_z
            })
        except Exception as e:
            print(f"[ERROR] Failed parsing segment {idx}: {e}")
            continue
            
    return segments

# hex_string = "8c c5 76 00 a5 aa f0 a2 c2 60 69 1e 00 00 00 81 00 04 6d 02 01 01 ff ff 5c 00 01 19 08 00 00 df c2 60 69 96 00 2c 00 96 00 00 ea c2 60 69 96 00 2c 00 96 00 00 f4 c2 60 69 96 00 2c 00 96 00 00 01 c3 60 69 96 00 2a 00 96 00 00 0b c3 60 69 96 00 28 00 96 00 00 16 c3 60 69 96 00 28 00 96 00 00 20 c3 60 69 96 00 24 00 96 00 00 2a c3 60 69 96 00 22 00 96 00 a2 9e 79 f8 b7 f1 a0 57 cc 3d 17 1c 20 06 99 47 1e 50 87 30 8f 4a 48 d2 55 0b 84 69 99 8c 9a 44 3a ba"

# print(HEALTH_ADCS_MGTRQR_CMD(hex_string.replace(" ","")))