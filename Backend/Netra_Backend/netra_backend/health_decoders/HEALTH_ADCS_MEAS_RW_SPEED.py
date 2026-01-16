
import struct 
from datetime import datetime

def HEALTH_ADCS_MEAS_RW_SPEED(hex_str):
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
    
    # Segment Length = 14 bytes = 28 hex chars (OperationStatus(1) + Epoch(4) + N(1) + 4xSpeeds(8))
    segment_len_bytes = 14
    segment_len_chars = segment_len_bytes * 2
    
    segments = []
    
    for idx in range(count):
        start = idx * segment_len_chars
        end = start + segment_len_chars
        seg = data_payload[start:end]
        
        if len(seg) < segment_len_chars:
            break
            
        try:
            # Table 55: HM Reaction Wheel Speed measurement telemetry format (14 bytes)
            # Operation Status: 1 byte
            operation_status = int(seg[0:2], 16)
            
            # Epoch: 4 bytes (UINT32)
            epoch_hex = seg[2:10]
            epoch_time = struct.unpack('<I', bytes.fromhex(epoch_hex))[0]
            epoch_time_human = datetime.utcfromtimestamp(epoch_time).strftime('%Y-%m-%d %H:%M:%S')
            
            # Number of Reaction Wheels (N): 1 byte
            num_rw = int(seg[10:12], 16)
            
            # Measured Wheel Speeds: N * 2 bytes (INT16)
            # Assuming N=4 as per typical setup and documentation
            wheel_speeds = []
            for i in range(num_rw):
                s_start = 12 + (i * 4)
                s_end = s_start + 4
                if s_end <= len(seg):
                    speed = struct.unpack('<h', bytes.fromhex(seg[s_start:s_end]))[0]
                    wheel_speeds.append(speed)
            
            res = {
                'Submodule_ID':         submodule_id,
                'Queue_ID':             queue_id,
                'Number_of_Instances':  count,
                'Operation_Status':     operation_status,
                'Epoch_Time_Human':     epoch_time_human,
                'Num_Reaction_Wheels':  num_rw
            }
            
            # Dynamically add wheel speeds to the dictionary
            for i, speed in enumerate(wheel_speeds):
                res[f'Measured_Wheel_Speed_{i+1}'] = speed
                
            segments.append(res)
        except Exception as e:
            print(f"[ERROR] Failed parsing segment {idx}: {e}")
            continue
            
    return segments

# Test hex string from pub.py
hex_string = "8c c5 74 00 a5 aa f0 a2 c2 60 69 1c 00 00 00 81 00 04 6d 02 01 01 ff ff 74 00 01 17 08 00 00 df c2 60 69 03 b6 01 fd fe 2c 00 f8 fe 00 ea c2 60 69 03 ab 01 01 ff 22 00 fa fe 00 f4 c2 60 69 03 9f 01 05 ff 19 00 fb fe 00 01 c3 60 69 03 8e 01 0c ff 0c 00 fe fe 00 0b c3 60 69 03 80 01 13 ff 03 00 00 ff 00 16 c3 60 69 03 71 01 1b ff fa ff 03 ff 00 20 c3 60 69 03 5f 01 24 ff ef ff 05 ff 00 2a c3 60 69 03 4f 01 2e ff e6 ff 08 ff 13 6f de fe 0e da d4 a7 a3 0b 87 9e 14 1c 9b 82 e3 61 bb 01 9b 0e 4b cb dc f0 f6 0f db 66 31 16 b5 ba"
print(HEALTH_ADCS_MEAS_RW_SPEED(hex_string.replace(" ","")))