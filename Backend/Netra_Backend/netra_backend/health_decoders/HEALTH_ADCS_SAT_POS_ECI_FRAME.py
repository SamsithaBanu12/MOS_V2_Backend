import struct
from datetime import datetime, timezone

def HEALTH_ADCS_SAT_POS_ECI_FRAME(hex_str):
    # 1. Skip standard metadata header (26 bytes)
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
    
    # Segment Length = 29 bytes = 58 hex chars (As per Table 69)
    segment_len_bytes = 29
    segment_len_chars = segment_len_bytes * 2
    
    segments = []
    for idx in range(count):
        start = idx * segment_len_chars
        end = start + segment_len_chars
        seg_hex = data_payload[start:end]
        
        if len(seg_hex) < segment_len_chars:
            break
            
        try:
            # Layout (Table 69): Operation Status (1B), Epoch Time (4B), X (8B double), Y (8B double), Z (8B double)
            # Struct format: < B (1), I (4), d (8), d (8), d (8)
            op_status, epoch_ti, pos_x, pos_y, pos_z = struct.unpack('<BIddd', bytes.fromhex(seg_hex))
            
            # Convert epoch integer to human-readable format (UTC)
            timestamp_human = datetime.fromtimestamp(epoch_ti, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            
            segments.append({
                'Submodule_ID': submodule_id,
                'Queue_ID': queue_id,
                'Number of Instances': count,
                'Operation_Status': op_status,
                'Epoch_Time_Human': timestamp_human,
                'Sat_Pos_ECI_X': pos_x,
                'Sat_Pos_ECI_Y': pos_y,
                'Sat_Pos_ECI_Z': pos_z,
            })
        except Exception as e:
            print(f"[ERROR] Failed parsing SAT_POS_ECI_FRAME segment {idx}: {e}")
            continue
            
    return segments

if __name__ == "__main__":
    # Test case with similar metadata
    hex_string = "8cc57500a5aaf0a2c260691d0000008100046d020101ffff7400011f080000dfc2606900000000000000000000000000000000000000000000000000eac2606900000000000000000000000000000000000000000000000000f4c260690000000000000000000000000000000000000000000000000001c36069000000000000000000000000000000000000000000000000000bc360690000000000000000000000000000000000000000000000000016c360690000000000000000000000000000000000000000000000000020c36069000000000000000000000000000000000000000000000000002ac360690000000000000000000000000000000000000000000000"
    results = HEALTH_ADCS_SAT_POS_ECI_FRAME(hex_string.replace(" ", ""))
    for r in results:
        print(r)
