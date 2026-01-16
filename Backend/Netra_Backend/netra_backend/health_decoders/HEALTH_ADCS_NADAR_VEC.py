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

hex_string = "8cc57e00a5aaf0a2c26069190000008100046d020101ffff5c00010b080000dfc26069c40308ff5a0000eac26069ca0312ff170000f4c26069cc031bffd7ff0001c36069c70325ff84ff000bc36069be032eff41ff0016c36069b00336fffffe0020c360699e033effc0fe002ac36069870345ff80fef3a1ff0965e0ccf84e71f31d0eb8430a0b3d37f0c2779c07c04a454981bc6cf7c6ba"

print(HEALTH_ADCS_NADAR_VEC(hex_string.replace(" ","")))
