import struct
from datetime import datetime

def HEALTH_ADCS_POS_LLH(hex_str):
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
    
    # Number of instances: 2 bytes (UINT16) at bytes 28-29
    count_hex = hex_str[header_skip_chars+4 : header_skip_chars+8]
    count = struct.unpack('<H', bytes.fromhex(count_hex))[0]
    
    if count == 0:
        print(f"[WARN] Sensor count is zero (Parsed from hex: {count_hex}). Skipping parsing.")
        return []

    # 3. Data payload starts at byte 30
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
            # Layout (Table 61): Operation Status (B), Epoch Time (I), Longitude (h), Latitude (h), Altitude (h)
            # '<B I h h h' = 1 + 4 + 2 + 2 + 2 = 11 bytes
            op_status, epoch_ti, raw_lon, raw_lat, raw_alt = struct.unpack('<BIhhh', bytes.fromhex(seg))
            
            # Scales as per Table 61:
            # Longitude = RAWVAL * 0.01
            # Latitude = RAWVAL * 0.01
            # Altitude = RAWVAL * 0.1
            longitude = raw_lon * 0.01
            latitude = raw_lat * 0.01
            altitude = raw_alt * 0.1
            
            # Convert epoch integer to human-readable format
            timestamp_human = datetime.utcfromtimestamp(epoch_ti).strftime('%Y-%m-%d %H:%M:%S')
            
            segments.append({
                'Submodule_ID': submodule_id,
                'Queue_ID': queue_id,
                'Number of Instances': count,
                'Operation_Status': op_status,
                'Epoch_Time_Human': timestamp_human,
                'Geocentric_Longitude': longitude,
                'Geocentric_Latitude': latitude,
                'Geocentric_Altitude': altitude,
            })
        except Exception as e:
            print(f"[ERROR] Failed parsing ADCS_POS_LLH segment {idx}: {e}")
            continue
            
    return segments
hex_string = "8c c5 79 00 a5 aa f0 a2 c2 60 69 21 00 00 00 81 00 04 6d 02 01 01 ff ff 5c 00 01 1a 08 00 00 df c2 60 69 54 13 ef ee 00 0c 00 ea c2 60 69 ad 13 e1 ee 00 0c 00 f4 c2 60 69 06 14 d3 ee 00 0c 00 01 c3 60 69 73 14 c3 ee 01 0c 00 0b c3 60 69 cd 14 b7 ee 01 0c 00 16 c3 60 69 27 15 ac ee 01 0c 00 20 c3 60 69 82 15 a1 ee 01 0c 00 2a c3 60 69 db 15 97 ee 02 0c 5d 93 4b f0 87 99 e3 d0 04 97 c8 8c 91 f9 8c cc 41 bc e7 2f c8 c6 d0 78 9f ac a0 aa d8 e0 d7 db ef ba"
print(HEALTH_ADCS_POS_LLH(hex_string.replace(" ", "")))