
import struct 
from datetime import datetime
def HEALTH_ADCS_CMD_ATTITUDE_ANGLE(hex_str):
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
    
    # Segment Length = 37 bytes = 74 hex chars
    segment_len_bytes = 37
    segment_len_chars = segment_len_bytes * 2
    
    segments = []
    
    for idx in range(count):
        start = idx * segment_len_chars
        end = start + segment_len_chars
        
        seg = data_payload[start:end]
        
        if len(seg) < segment_len_chars:
            break
            
        # Segment Structure (37 bytes):
        # 0   (1 byte) : Operation Status (UINT)
        # 1-4 (4 bytes): Epoch Time (UINT)
        # 5-12(8 bytes): Commanded Roll Angle (DOUBLE) * 0.01
        # 13-20(8 bytes): Commanded Pitch Angle (DOUBLE) * 0.01
        # 21-28(8 bytes): Commanded Yaw Angle (DOUBLE) * 0.01
        # 29-36(8 bytes): Check/Quaternion (DOUBLE)
        
        try:
            offset = 0
            
            # Operation Status
            operation_status = int(seg[offset:offset+2], 16)
            offset += 2
            
            # Epoch Time
            epoch_hex = seg[offset:offset+8]
            epoch_time = struct.unpack('<I', bytes.fromhex(epoch_hex))[0]
            epoch_time_human = datetime.utcfromtimestamp(epoch_time).strftime('%Y-%m-%d %H:%M:%S')
            offset += 8
            
            # Roll (8 bytes)
            roll = struct.unpack('<d', bytes.fromhex(seg[offset:offset+16]))[0] * 0.01
            offset += 16
            
            # Pitch (8 bytes)
            pitch = struct.unpack('<d', bytes.fromhex(seg[offset:offset+16]))[0] * 0.01
            offset += 16
            
            # Yaw (8 bytes)
            yaw = struct.unpack('<d', bytes.fromhex(seg[offset:offset+16]))[0] * 0.01
            offset += 16
            
            # Check/Quaternion4 (8 bytes)
            val4 = struct.unpack('<d', bytes.fromhex(seg[offset:offset+16]))[0]
            offset += 16
            
            interpretation = "Quaternion"
            if val4 >= 2:
                interpretation = "RPY"
            
            segments.append({
                'Submodule_ID':         submodule_id,
                'Queue_ID':             queue_id,
                'Number_of_Instances':  count,
                'Operation_Status':     operation_status,
                'Epoch_Time_Human':     epoch_time_human,
                'Commanded_Roll':       roll,
                'Commanded_Pitch':      pitch,
                'Commanded_Yaw':        yaw,
                'Quaternion_4_Check':   val4,
                'Interpretation':       interpretation
            })
            
        except Exception as e:
            print(f"[ERROR] Failed parsing segment {idx}: {e}")
            continue
            
    return segments

hex_string = "8c c5 78 00 a5 aa f0 12 ff 26 69 3b 01 00 00 81 00 04 6d 02 01 01 ff ff 14 00 01 16 30 00 f8 c5 60 75 67 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 f8 d9 60 75 67 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 f8 e3 60 75 67 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 f8 ed 60 75 67 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 f8 f7 60 75 67 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 f8 01 61 75 67 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 f8 15 61 75 67 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 f8 1f 61 75 67 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 f8 29 61 75 67 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 f8 33 61 75 67 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 f8 3d 61 75 67 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 f8 51 61 75 67 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 f8 5b 61 75 67 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 f8 65 61 75 67 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 f8 6f 61 75 67 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 f8 79 61 75 67 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 f8 8d 61 75 67 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"
print(HEALTH_ADCS_CMD_ATTITUDE_ANGLE(hex_string.replace(" ","")))
