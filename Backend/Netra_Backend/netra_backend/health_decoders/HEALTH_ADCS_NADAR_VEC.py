import struct
from datetime import datetime


def HEALTH_ADCS_NADAR_VEC(hex_str):
    # hex_str is expected to be a continuous hex string (no spaces)
    
    # 1. First 26 bytes (52 hex chars) are simple skip
    header_skip_bytes = 26
    header_skip_chars = header_skip_bytes * 2
    
    # Ensure we have enough data for the header
    if len(hex_str) < (header_skip_chars + 8):
        print(f"[ERROR] Insufficient data length: {len(hex_str)}")
        return []

    # 2. Decoding follows little endian format
    
    # Submodule ID: 1 byte at offset 26
    submodule_id = int(hex_str[header_skip_chars : header_skip_chars+2], 16)
    
    # Queue ID: 1 byte at offset 27
    queue_id = int(hex_str[header_skip_chars+2 : header_skip_chars+4], 16)
    
    # Number of instances: 2 bytes at offset 28
    count_hex = hex_str[header_skip_chars+4 : header_skip_chars+8]
    count = struct.unpack('<H', bytes.fromhex(count_hex))[0]
    
    if count == 0:
        print("[WARN] Sensor count is zero. Skipping parsing.")
        return []

    # Data starts at offset 30 bytes (60 chars)
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
            
        # Segment Structure (11 bytes):
        # 0   (1 byte) : Operation Status (UINT)
        # 1-4 (4 bytes): Epoch Time (UINT)
        # 5-6 (2 bytes): X axis Nadir vector (INT) * 0.001
        # 7-8 (2 bytes): Y axis Nadir vector (INT) * 0.001
        # 9-10(2 bytes): Z axis Nadir vector (INT) * 0.001
        
        try:
            operation_status = int(seg[0:2], 16)
            
            epoch_bytes = bytes.fromhex(seg[2:10])
            epoch_time = struct.unpack('<I', epoch_bytes)[0]
            epoch_time_human = datetime.utcfromtimestamp(epoch_time).strftime('%Y-%m-%d %H:%M:%S')
            
            nadar_vector_x = struct.unpack('<h', bytes.fromhex(seg[10:14]))[0] * 0.001
            nadar_vector_y = struct.unpack('<h', bytes.fromhex(seg[14:18]))[0] * 0.001
            nadar_vector_z = struct.unpack('<h', bytes.fromhex(seg[18:22]))[0] * 0.001
            
            segments.append({
                'Submodule_ID':         submodule_id,
                'Queue_ID':             queue_id,
                'Number_of_Instances':  count,
                'Operation_Status':     operation_status,
                'Epoch_Time_Human':     epoch_time_human,
                'NADAR_Vector_X':       nadar_vector_x,
                'NADAR_Vector_Y':       nadar_vector_y,
                'NADAR_Vector_Z':       nadar_vector_z
            })
        except Exception as e:
            print(f"[ERROR] Failed parsing segment {idx}: {e}")
            continue
            
    return segments

hex_string = "8c c5 78 00 a5 aa f0 12 ff 26 69 3b 01 00 00 81 00 04 6d 02 01 01 ff ff 14 00 01 0b 30 00 f8 c5 60 75 67 00 00 00 00 00 00 f8 d9 60 75 67 00 00 00 00 00 00 f8 e3 60 75 67 00 00 00 00 00 00 f8 ed 60 75 67 00 00 00 00 00 00 f8 f7 60 75 67 00 00 00 00 00 00 f8 01 61 75 67 00 00 00 00 00 00 f8 15 61 75 67 00 00 00 00 00 00 f8 1f 61 75 67 00 00 00 00 00 00 f8 29 61 75 67 00 00 00 00 00 00 f8 33 61 75 67 00 00 00 00 00 00 f8 3d 61 75 67 00 00 00 00 00 00 f8 51 61 75 67 00 00 00 00 00 00 f8 5b 61 75 67 00 00 00 00 00 00 f8 65 61 75 67 00 00 00 00 00 00 f8 6f 61 75 67 00 00 00 00 00 00 f8 79 61 75 67 00 00 00 00 00 00 f8 8d 61 75 67 00 00 00 00 00 00 f8 97 61 75 67 00 00 00 00 00 00 f8 a1 61 75 67 00 00 00 00 00 00 f8 ab 61 75 67 00 00 00 00 00 00 f8 b5 61 75 67 00 00 00 00 00 00 f8 c9 61 75 67 00 00 00 00 00 00 f8 d3 61 75 67 00 00 00 00 00 00 f8 dd 61 75 67 00 00 00 00 00 00 f8 e7 61 75 67 00 00 00 00 00 00 f8 f1 61 75 67 00 00 00 00 00 00 f8 05 62 75 67 00 00 00 00 00 00 f8 0f 62 75 67 00 00 00 00 00 00 f8 19 62 75 67 00 00 00 00 00 00 f8 23 62 75 67 00 00 00 00 00 00 f8 2d 62 75 67 00 00 00 00 00 00 f8 41 62 75 67 00 00 00 00 00 00 f8 4b 62 75 67 00 00 00 00 00 00 f8 55 62 75 67 00 00 00 00 00 00 f8 5f 62 75 67 00 00 00 00 00 00 f8 69 62 75 67 00 00 00 00 00 00 f8 7d 62 75 67 00 00 00 00 00 00 f8 87 62 75 67 00 00 00 00 00 00 f8 91 62 75 67 00 00 00 00 00 00 f8 9b 62 75 67 00 00 00 00 00 00 f8 a5 62 75 67 00 00 00 00 00 00 f8 b9 62 75 67 00 00 00 00 00 00 f8 c3 62 75 67 00 00 00 00 00 00 f8 cd 62 75 67 00 00 00 00 00 00 f8 d7 62 75 67 00 00 00 00 00 00 f8 e1 62 75 67 00 00 00 00 00 00 f8 f5 62 75 67 00 00 00 00 00 00 f8 ff 62 75 67 00 00 00 00 00 00"

print(HEALTH_ADCS_NADAR_VEC(hex_string.replace(" ","")))
