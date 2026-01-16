
import struct 
from datetime import datetime, timezone

def HEALTH_ADCS_CSS_VECTOR(hex_str):
    # hex_str is expected to be a continuous hex string (no spaces)
    
    # 1. First 26 bytes (52 hex chars) are metadata skip
    header_skip_bytes = 26
    header_skip_chars = header_skip_bytes * 2
    
    # Ensure we have enough data for the header (Submodule + Queue + NumInstance = 4 bytes)
    if len(hex_str) < (header_skip_chars + 8): 
        print(f"[ERROR] Insufficient data length: {len(hex_str)}")
        return []

    # 2. Decoding follows little endian format
    
    # Submodule ID: byte 26
    submodule_id = int(hex_str[header_skip_chars : header_skip_chars+2], 16)
    
    # Queue ID: byte 27
    queue_id = int(hex_str[header_skip_chars+2 : header_skip_chars+4], 16)
    
    # Number of instances: 2 bytes at byte 28-29
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
            # Segment Structure:
            # Status: uint8 (1 byte)
            operation_status = int(seg[0:2], 16)
            
            # Epoch Time: uint32 (4 bytes)
            epoch_hex = seg[2:10]
            epoch_time = struct.unpack('<I', bytes.fromhex(epoch_hex))[0]
            # Formatted string for human readability (DB client will now detect this as TIMESTAMP)
            epoch_time_human = datetime.fromtimestamp(epoch_time, tz=timezone.utc)
            
            # Sun Vector X, Y, Z: int16 (2 bytes each) * 0.001
            css_vector_x = struct.unpack('<h', bytes.fromhex(seg[10:14]))[0] * 0.001
            css_vector_y = struct.unpack('<h', bytes.fromhex(seg[14:18]))[0] * 0.001
            css_vector_z = struct.unpack('<h', bytes.fromhex(seg[18:22]))[0] * 0.001
            
            segments.append({
                'Submodule_ID':         submodule_id,
                'Queue_ID':             queue_id,
                'Number_of_Instances':  count,
                'Operation_Status':     operation_status,
                'Epoch_Time_Human':     epoch_time_human,
                'Sun_Vector_X':         css_vector_x,
                'Sun_Vector_Y':         css_vector_y,
                'Sun_Vector_Z':         css_vector_z
            })
        except Exception as e:
            print(f"[ERROR] Failed parsing segment {idx}: {e}")
            continue
            
    return segments

# Test hex string with 26-byte skip, then Submodule(01), Queue(07), Count(08 00)
# Then 11-byte segments

