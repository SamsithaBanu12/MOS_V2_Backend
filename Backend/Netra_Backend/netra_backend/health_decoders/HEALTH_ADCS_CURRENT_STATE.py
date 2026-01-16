import struct
from datetime import datetime


def HEALTH_ADCS_CURRENT_STATE(hex_str):
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
    
    # Segment Length = 15 bytes = 30 hex chars (User field feedback: Reserved is 8 bytes)
    segment_len_bytes = 15
    segment_len_chars = segment_len_bytes * 2
    
    segments = []
    
    for idx in range(count):
        start = idx * segment_len_chars
        end = start + segment_len_chars
        
        seg = data_payload[start:end]
        
        if len(seg) < segment_len_chars:
            break
            
        # Segment Structure (14 bytes):
        # 0   (1 byte) : Operation Status (UINT)
        # 1-4 (4 bytes): Epoch Time (UINT)
        # 5   (1 byte) : Attitude Estimation Mode (ENUM)
        # 6   (1 byte) : Control Mode (ENUM)
        # 7-13(7 bytes): Reserved
        
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
            
            # Attitude Estimation Mode
            attitude_val = int(seg[offset:offset+2], 16)
            offset += 2
            attitude_modes = {
                1: "ADCS_EST_MODE_RAW",
                2: "ADCS_EST_MODE_FG_WO_IMU",
                3: "ADCS_EST_MODE_FG",
                4: "ADCS_EST_MODE_KALMAN",
                5: "ADCS_EST_MODE_KALMAN_B"
            }
            attitude_estimation_mode = attitude_modes.get(attitude_val, f"UNKNOWN({attitude_val})")
            
            # Control Mode
            control_val = int(seg[offset:offset+2], 16)
            offset += 2
            control_modes = {
                4: "ADCS_CTRL_MODE_THREE_AXIS",
                5: "ADCS_CTRL_MODE_SUN_POINTING",
                6: "ADCS_CTRL_MODE_NADIR_POINTING",
                7: "ADCS_CTRL_MODE_TARGET_TRACKING",
                8: "ADCS_CTRL_MODE_FINE_SUN_POINTING"
            }
            control_mode = control_modes.get(control_val, f"UNKNOWN({control_val})")
            
            # Reserved (skip 14 hex chars = 7 bytes)
            # offset += 14
            
            segments.append({
                'Submodule_ID': submodule_id,
                'Queue_ID': queue_id,
                'Number of Instances': count,
                'operation_status': operation_status,
                'epoch_time_human': epoch_time_human,
                'attitude_estimation_mode': attitude_estimation_mode,
                'control_mode': control_mode
            })
            
        except Exception as e:
            print(f"[ERROR] Failed parsing segment {idx}: {e}")
            continue
            
    return segments

hx_string = "8c c5 7b 00 a5 aa f0 a2 c2 60 69 16 00 00 00 81 00 04 6d 02 01 01 ff ff 7c 00 01 06 08 00 00 df c2 60 69 04 05 a8 6a 16 56 55 00 c0 07 00 ea c2 60 69 04 05 a8 6a 56 56 55 00 c0 07 00 f4 c2 60 69 04 05 a8 6a 56 56 55 00 c0 07 00 01 c3 60 69 04 05 a8 6a 56 56 55 00 c0 07 00 0b c3 60 69 04 05 a8 6a 56 56 55 00 c0 07 00 16 c3 60 69 04 05 a8 6a 56 56 55 00 c0 07 00 20 c3 60 69 04 05 a8 6a 56 56 55 00 c0 07 00 2a c3 60 69 04 05 a8 6a 56 56 55 00 c0 07 49 42 19 a6 29 40 43 f4 db 1d 6f 79 af 3c d6 74 f5 cc 36 2d 33 65 83 4d 1d c3 3d 54 75 3e db c2 63 ba"

print(HEALTH_ADCS_CURRENT_STATE(hx_string.replace(" ","")))