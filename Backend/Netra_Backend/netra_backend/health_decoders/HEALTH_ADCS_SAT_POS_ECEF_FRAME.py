import struct
from datetime import datetime, timezone

def HEALTH_ADCS_SAT_POS_ECEF_FRAME(hex_str):
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
    
    # Segment Length = 29 bytes = 58 hex chars (As per Table 67)
    segment_len_bytes = 29
    segment_len_chars = segment_len_bytes * 2
    
    segments = []
    for idx in range(count):
        start = idx * segment_len_chars
        end = start + segment_len_chars
        seg = data_payload[start:end]
        
        if len(seg) < segment_len_chars:
            break
            
        try:
            # Layout (Table 67): Operation Status (1B), Epoch Time (4B), X (8B double), Y (8B double), Z (8B double)
            # Struct format: < B (1), I (4), d (8), d (8), d (8)
            op_status, epoch_ti, pos_x, pos_y, pos_z = struct.unpack('<BIddd', bytes.fromhex(seg))
            
            # Convert epoch integer to human-readable format (UTC)
            timestamp_human = datetime.fromtimestamp(epoch_ti, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            
            segments.append({
                'Submodule_ID': submodule_id,
                'Queue_ID': queue_id,
                'Number of Instances': count,
                'Operation_Status': op_status,
                'Epoch_Time_Human': timestamp_human,
                'Sat_Pos_ECEF_X': pos_x,
                'Sat_Pos_ECEF_Y': pos_y,
                'Sat_Pos_ECEF_Z': pos_z,
            })
        except Exception as e:
            print(f"[ERROR] Failed parsing SAT_POS_ECEF_FRAME segment {idx}: {e}")
            continue
            
    return segments

if __name__ == "__main__":
    # Test case with similar metadata to previous working examples
    hex_string = "8cc57f00a5aaf0a2c26069270000008100046d020101ffffec00011e080000dfc260699a9241f95d92a840d3d420e86bc1ac4049d36a357df3b1c000eac2606970af80de9a10a840f0227b6fc10fad409ddff247d9ffb1c000f4c260697ca86cc8128ea740be1d6f16375dad4040b49a368a0bb2c00001c36069fc09858063eca640e1f002b255bbad40409efe3e0219b2c0000bc36069cd906aa5c06aa640e270185e5d05ae401ab218520323b2c00016c36069ae772454dee5a540dbab5dd9f24fae40068460d38b2cb2c00020c36069e46324084a60a540fe19b5d99d99ae40bce80a896735b2c0002ac36069ade2d75208daa440ac7c72ec5be2ae40f6571d1f963db2c08a3d201f3014dfb38506617601a776d55f502a191058464dc655494496655ca066ba"
    results = HEALTH_ADCS_SAT_POS_ECEF_FRAME(hex_string.replace(" ", ""))
    for r in results:
        print(r)