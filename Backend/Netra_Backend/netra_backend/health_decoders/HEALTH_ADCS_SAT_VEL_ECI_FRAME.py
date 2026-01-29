import struct
from datetime import datetime, timezone

def HEALTH_ADCS_SAT_VEL_ECI_FRAME(hex_str):
    # 1. Skip standard metadata header (26 bytes)
    header_skip_bytes = 26
    header_skip_chars = header_skip_bytes * 2
    
    if len(hex_str) < (header_skip_chars + 8):
        # Need at least header + 1B sub + 1B queue + 2B count
        return []

    # 2. Decoding QM metadata
    submodule_id = int(hex_str[header_skip_chars : header_skip_chars+2], 16)
    queue_id = int(hex_str[header_skip_chars+2 : header_skip_chars+4], 16)
    
    # Instance count (UINT16 at bytes 28-29)
    count_hex = hex_str[header_skip_chars+4 : header_skip_chars+8]
    count = struct.unpack('<H', bytes.fromhex(count_hex))[0]
    
    if count == 0:
        print(f"[WARN] Sensor count is zero. Skipping parsing.")
        return []

    # 3. Data payload starts at byte 30
    # Each segment is 29 bytes:
    # 1 byte Operation Status
    # 4 bytes Epoch Time
    # 8 bytes X Velocity (Double)
    # 8 bytes Y Velocity (Double)
    # 8 bytes Z Velocity (Double)
    segment_bytes = 1 + 4 + 8 + 8 + 8
    segment_chars = segment_bytes * 2

    data_start_idx = header_skip_chars + 8
    data_payload = hex_str[data_start_idx:]
    
    segments = []
    
    for idx in range(count):
        start_char = idx * segment_chars
        end_char = start_char + segment_chars
        
        if len(data_payload) < end_char:
            break
            
        seg_hex = data_payload[start_char : end_char]
        
        try:
            # Unpack: B (1), I (4), d (8), d (8), d (8)
            # Total 29 bytes
            operation_status, epoch_time, vx, vy, vz = struct.unpack('<BIddd', bytes.fromhex(seg_hex))
            
            # Using timezone-aware UTC datetime
            epoch_time_human = datetime.fromtimestamp(epoch_time, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            
            segments.append({
                'Submodule_ID': submodule_id,
                'Queue_ID': queue_id,
                'Number of Instances': count,
                'Operation_Status': operation_status,
                'Epoch_Time_Human': epoch_time_human,
                'Sat_Vel_ECI_X': vx,
                'Sat_Vel_ECI_Y': vy,
                'Sat_Vel_ECI_Z': vz
            })
        except struct.error as e:
            print(f"[ERROR] Struct unpack failed for instance {idx}: {e}")
            continue

    return segments

