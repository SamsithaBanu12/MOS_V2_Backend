
import struct 
from datetime import datetime, timezone

def HEALTH_ADCS_IGRF_MOD_VEC(hex_str):
    # hex_str is expected to be a continuous hex string (no spaces)
    
    # 1. First 26 bytes (52 hex chars) are metadata skip (OpenC3 preamble)
    header_skip_bytes = 26
    header_skip_chars = header_skip_bytes * 2
    
    # Ensure we have enough data for the health header (Submodule + Queue + NumInstance = 4 bytes)
    if len(hex_str) < (header_skip_chars + 8): 
        print(f"[ERROR] Insufficient data length: {len(hex_str)}")
        return []

    # 2. Decoding follows little endian format
    
    # Submodule ID: byte 26
    submodule_id = int(hex_str[header_skip_chars : header_skip_chars+2], 16)
    
    # Queue ID: byte 27
    queue_id = int(hex_str[header_skip_chars+2 : header_skip_chars+4], 16)
    
    # Number of instances: 2 bytes at byte 28-29 (UINT16)
    count_hex = hex_str[header_skip_chars+4 : header_skip_chars+8]
    count = struct.unpack('<H', bytes.fromhex(count_hex))[0]
    
    if count == 0:
        print(f"[WARN] Sensor count is zero (Parsed from hex: {count_hex}). Skipping parsing.")
        return []

    # 3. Data starts at byte 30
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
            
        try:
            # Table 38: HM Modelled Magnetic field vector measurement format (11 bytes)
            # Operation Status: 1 byte
            operation_status = int(seg[0:2], 16)
            
            # Epoch Time: 4 bytes (UINT32)
            epoch_hex = seg[2:10]
            epoch_time = struct.unpack('<I', bytes.fromhex(epoch_hex))[0]
            # Returns datetime object for DB worker to handle correctly
            epoch_time_human = datetime.utcfromtimestamp(epoch_time).strftime('%Y-%m-%d %H:%M:%S')
            
            # IGRF Mod Vector X, Y, Z: 2 bytes each (INT16) * 0.01 μT
            igrf_mod_vector_x = struct.unpack('<h', bytes.fromhex(seg[10:14]))[0] * 0.01
            igrf_mod_vector_y = struct.unpack('<h', bytes.fromhex(seg[14:18]))[0] * 0.01
            igrf_mod_vector_z = struct.unpack('<h', bytes.fromhex(seg[18:22]))[0] * 0.01
            
            segments.append({
                'Submodule_ID':         submodule_id,
                'Queue_ID':             queue_id,
                'Number_of_Instances':  count,
                'Operation_Status':     operation_status,
                'Epoch_Time_Human':     epoch_time_human,
                'IGRF_Mod_Vector_X':    igrf_mod_vector_x,
                'IGRF_Mod_Vector_Y':    igrf_mod_vector_y,
                'IGRF_Mod_Vector_Z':    igrf_mod_vector_z
            })
        except Exception as e:
            print(f"[ERROR] Failed parsing segment {idx}: {e}")
            continue
            
    return segments

