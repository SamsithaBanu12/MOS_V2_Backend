import struct
from datetime import datetime, timezone

def HEALTH_ADCS_RW_SPEED_CMD(hex_str):
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
        print(f"[WARN] Sensor count is zero (Parsed from hex: {count_hex}). Skipping parsing.")
        return []

    # 3. Data payload starts at byte 30
    data_start_idx = header_skip_chars + 8
    data_payload = hex_str[data_start_idx:]
    
    segments = []
    pos_chars = 0
    
    for idx in range(count):
        # We need at least 6 bytes (12 hex chars) to read the fixed part
        # Offset 0: Operation Status (1B)
        # Offset 1: Epoch Time (4B)
        # Offset 5: n (1B)
        if len(data_payload[pos_chars:]) < 12:
            break
            
        header_hex = data_payload[pos_chars : pos_chars + 12]
        try:
            # Layout follows Table 57: B (1), I (4), B (1)
            op_status, epoch_ti, n_wheels = struct.unpack('<BI B', bytes.fromhex(header_hex))
            
            # Segment length = 6 + 2*n bytes
            seg_len_bytes = 6 + 2 * n_wheels
            seg_len_chars = seg_len_bytes * 2
            
            if len(data_payload[pos_chars:]) < seg_len_chars:
                print(f"[ERROR] Incomplete segment for instance {idx}. Needed {seg_len_bytes} bytes.")
                break
                
            full_seg_hex = data_payload[pos_chars : pos_chars + seg_len_chars]
            speeds_data = full_seg_hex[12:]
            
            row = {
                'Submodule_ID': submodule_id,
                'Queue_ID': queue_id,
                'Number of Instances': count,
                'Operation_Status': op_status,
                'Epoch_Time_Human': datetime.fromtimestamp(epoch_ti, timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                'Number_of_reaction_wheel': n_wheels
            }
            
            # According to manual N=3, but we handle it dynamically
            for i in range(n_wheels):
                speed_hex = speeds_data[i*4 : (i+1)*4]
                if speed_hex:
                    # Wheel commanded speed (unit is RPM, usually 16-bit)
                    # Note: Manual says -8000 to 8000 RPM, so signed short 'h' is likely
                    speed_val = struct.unpack('<h', bytes.fromhex(speed_hex))[0]
                    row[f'Command_Wheel_Speed_{i+1}'] = speed_val
            
            segments.append(row)
            pos_chars += seg_len_chars
            
        except Exception as e:
            print(f"[ERROR] Failed parsing segment {idx}: {e}")
            break
            
    return segments

hex_string = "8cc57500a5aaf0a2c260691d0000008100046d020101ffff74000118080000dfc2606904000000000000000000eac2606904000000000000000000f4c260690400000000000000000001c36069040000000000000000000bc360690400000000000000000016c360690400000000000000000020c36069040000000000000000002ac36069040000000000000000d42472a110524babd6d392f39529fbd56dbb0daad932812339762c49411772ebcfba"
results = HEALTH_ADCS_RW_SPEED_CMD(hex_string.replace(' ', ''))
for r in results:
    print(r)