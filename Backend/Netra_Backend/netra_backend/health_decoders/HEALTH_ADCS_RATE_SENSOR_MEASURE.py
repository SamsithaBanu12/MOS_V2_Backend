import struct
from datetime import datetime


def HEALTH_ADCS_RATE_SENSOR_MEASURE(hex_str):
    # hex_str is expected to be a continuous hex string (no spaces)
    
    # 1. First 26 bytes (52 hex chars) are simple skip
    header_skip_bytes = 26
    header_skip_chars = header_skip_bytes * 2
    
    # Ensure we have enough data for the header
    if len(hex_str) < (header_skip_chars + 8): # 26 skip + 1 sub + 1 queue + 2 count = 30 bytes min
        print("[ERROR] Insufficient data length.")
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
    
    segment_len_bytes = 11
    segment_len_chars = segment_len_bytes * 2
    
    segments = []
    
    for idx in range(count):
        start = idx * segment_len_chars
        end = start + segment_len_chars
        
        seg = data_payload[start:end]
        
        if len(seg) < segment_len_chars:
            break
            
        # Segment Structure:
        # 0   (1 byte) : Operation Status (UINT)
        # 1-4 (4 bytes): Epoch Time (UINT)
        # 5-6 (2 bytes): Measured X (INT)
        # 7-8 (2 bytes): Measured Y (INT)
        # 9-10(2 bytes): Measured Z (INT)
        
        operation_status = int(seg[0:2], 16)
        
        epoch_bytes = bytes.fromhex(seg[2:10])
        epoch_time = struct.unpack('<I', epoch_bytes)[0]
        epoch_time_human = datetime.utcfromtimestamp(epoch_time).strftime('%Y-%m-%d %H:%M:%S')
        
        rate_sensor_x = struct.unpack('<h', bytes.fromhex(seg[10:14]))[0] * 0.01
        rate_sensor_y = struct.unpack('<h', bytes.fromhex(seg[14:18]))[0] * 0.01
        rate_sensor_z = struct.unpack('<h', bytes.fromhex(seg[18:22]))[0] * 0.01
        
        segments.append({
            'Submodule_ID':         submodule_id,
            'Queue_ID':             queue_id,
            'Number of Instances':  count,
            'Operation_Status':     operation_status,
            'Epoch_Time_Human':     epoch_time_human,
            'Measured_rate_X':      rate_sensor_x,
            'Measured_rate_Y':      rate_sensor_y,
            'Measured_rate_Z':      rate_sensor_z
        })
        
    return segments
