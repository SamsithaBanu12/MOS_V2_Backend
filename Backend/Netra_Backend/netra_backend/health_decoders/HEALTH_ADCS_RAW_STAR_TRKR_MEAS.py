import struct
from datetime import datetime, timezone

def HEALTH_ADCS_RAW_STAR_TRKR_MEAS(hex_str):
    # 1. Skip metadata header (26 bytes)
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
    
    # Segment Length = 47 bytes = 94 hex chars (Table 47/48)
    segment_len_bytes = 47
    segment_len_chars = segment_len_bytes * 2
    
    segments = []
    for idx in range(count):
        start = idx * segment_len_chars
        end = start + segment_len_chars
        seg_hex = data_payload[start:end]
        
        if len(seg_hex) < segment_len_chars:
            break
            
        try:
            # Segment Structure (Table 48):
            # 0   (1 byte) : Operation Status
            # 1-4 (4 bytes): Epoch Time
            # 5   (1 byte) : Num stars detected
            # 6-7 (2 bytes): Reserved
            # 8   (1 byte) : Num star identified
            # 9   (1 byte) : Identification mode (ENUM)
            # 10-46 (37 bytes): Reserved
            
            # Extract only the fields we need (first 10 bytes)
            fixed_fields = bytes.fromhex(seg_hex[0 : 20])
            op_status, epoch_ti, num_detected, _, num_identified, mode_val = struct.unpack('<BI B H B B', fixed_fields)
            
            # Convert epoch integer to human-readable format (UTC)
            timestamp_human = datetime.fromtimestamp(epoch_ti, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            
            # Star Tracker identification mode (Table 49)
            mode_enum = {
                0: "ADCS_STAR_MODE_TRACKING",
                1: "ADCS_STAR_MODE_LOST"
            }
            identification_mode = mode_enum.get(mode_val, f"UNKNOWN({mode_val})")
            
            segments.append({
                'Submodule_ID': submodule_id,
                'Queue_ID': queue_id,
                'Number of Instances': count,
                'Operation_Status': op_status,
                'Epoch_Time_Human': timestamp_human,
                'Num_Stars_Detected': num_detected,
                'Num_Star_Identified': num_identified,
                'Identification_Mode': identification_mode,
            })
        except Exception as e:
            print(f"[ERROR] Failed parsing ADCS_RAW_STAR_TRKR_MEAS segment {idx}: {e}")
            continue
            
    return segments
