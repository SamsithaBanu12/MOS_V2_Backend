import struct
from datetime import datetime, timezone

def HEALTH_ADCS_RW_CURRENT(hex_str):
    # 1. Skip standard metadata header (26 bytes)
    header_skip_bytes = 26
    header_skip_chars = header_skip_bytes * 2
    
    if len(hex_str) < (header_skip_chars + 8):
        print(f"[ERROR] Insufficient data length: {len(hex_str)}")
        return []

    # 2. Decoding QM metadata
    submodule_id = int(hex_str[header_skip_chars : header_skip_chars+2], 16)
    queue_id = int(hex_str[header_skip_chars+2 : header_skip_chars+4], 16)
    
    # Instance count (UINT16 at bytes 28-29)
    count_hex = hex_str[header_skip_chars+4 : header_skip_chars+8]
    count = struct.unpack('<H', bytes.fromhex(count_hex))[0]
    
    if count == 0:
        return []

    # 3. Data payload starts at byte 30
    data_start_idx = header_skip_chars + 8
    data_payload = hex_str[data_start_idx:]
    
    segments = []
    pos_chars = 0
    
    for idx in range(count):
        # We need at least 6 bytes (12 hex chars) to read the fixed part of the segment
        # Offset 0: Operation Status (1B)
        # Offset 1: Epoch Time (4B)
        # Offset 5: n (1B)
        if len(data_payload[pos_chars:]) < 12:
            break
            
        header_hex = data_payload[pos_chars : pos_chars + 12]
        try:
            # Layout follows Table 22 strictly: < B (1), I (4), B (1)
            op_status, epoch_ti, n_wheels = struct.unpack('<BI B', bytes.fromhex(header_hex))
            
            # Full segment length = 6 + 2*n bytes
            seg_len_bytes = 6 + 2 * n_wheels
            seg_len_chars = seg_len_bytes * 2
            
            if len(data_payload[pos_chars:]) < seg_len_chars:
                print(f"[ERROR] Incomplete segment for instance {idx}")
                break
                
            full_seg_hex = data_payload[pos_chars : pos_chars + seg_len_chars]
            # Currents start at offset 6 (char 12)
            currents_data = full_seg_hex[12:]
            
            # Construct row FOLLOWING TABLE ORDER
            row = {
                'Submodule_ID': submodule_id,
                'Queue_ID': queue_id,
                'Number of Instances': count,
                'Operation_Status': op_status,
                'Epoch_Time_Human': datetime.fromtimestamp(epoch_ti, timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                'Number_of_reaction_wheel': n_wheels
            }
            
            # Initialize 4 standard current columns to ensure DB schema stability
            for i in range(1, 5):
                row[f'Reaction_wheel_current_{i}'] = None
                
            # Fill existing wheel data
            for i in range(n_wheels):
                cur_hex = currents_data[i*4 : (i+1)*4]
                if cur_hex:
                    raw_val = struct.unpack('<H', bytes.fromhex(cur_hex))[0]
                    # Current = RAWVAL * 0.1
                    row[f'Reaction_wheel_current_{i+1}'] = round(raw_val * 0.1, 2)
            
            segments.append(row)
            pos_chars += seg_len_chars
            
        except Exception as e:
            print(f"[ERROR] Failed parsing segment {idx}: {e}")
            break
            
    return segments

