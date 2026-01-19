import struct
from datetime import datetime, timezone


def HEALTH_ADCS_CURRENT_STATE(hex_str):
    # 1. Skip common metadata header (26 bytes)
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
        print("[WARN] Sensor count is zero. Skipping parsing.")
        return []

    # 3. Data payload starts at byte 30
    data_start_idx = header_skip_chars + 8
    data_payload = hex_str[data_start_idx:]
    
    # Segment Length = 14 bytes = 28 hex chars (As per Table 28 in reference manual)
    segment_len_bytes = 14
    segment_len_chars = segment_len_bytes * 2
    
    segments = []
    for idx in range(count):
        start = idx * segment_len_chars
        end = start + segment_len_chars
        seg = data_payload[start:end]
        
        if len(seg) < segment_len_chars:
            break
            
        try:
            # Segment Structure (Table 28 - 14 bytes total):
            # 0   (1 byte) : Operation Status (UINT)
            # 1-4 (4 bytes): Epoch Time (UINT)
            # 5   (1 byte) : Attitude Estimation Mode (ENUM)
            # 6   (1 byte) : Control Mode (ENUM)
            # 7-13(7 bytes): Reserved
            
            operation_status, epoch_ti, est_mode_val, ctrl_mode_val = struct.unpack('<BI BB', bytes.fromhex(seg[0:14]))
            
            # Epoch conversion
            timestamp_human = datetime.fromtimestamp(epoch_ti, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            
            # Attitude Estimation Mode (Table 29)
            attitude_modes = {
                1: "ADCS_EST_MODE_RAW",
                2: "ADCS_EST_MODE_FG_WO_IMU",
                3: "ADCS_EST_MODE_FG",
                4: "ADCS_EST_MODE_KALMAN",
                5: "ADCS_EST_MODE_KALMAN_B"
            }
            attitude_estimation_mode = attitude_modes.get(est_mode_val, f"UNKNOWN({est_mode_val})")
            
            # Control Mode (Table 30)
            control_modes = {
                4: "ADCS_CTRL_MODE_THREE_AXIS",
                5: "ADCS_CTRL_MODE_SUN_POINTING",
                6: "ADCS_CTRL_MODE_NADIR_POINTING",
                7: "ADCS_CTRL_MODE_TARGET_TRACKING",
                8: "ADCS_CTRL_MODE_FINE_SUN_POINTING"
            }
            control_mode = control_modes.get(ctrl_mode_val, f"UNKNOWN({ctrl_mode_val})")
            
            segments.append({
                'Submodule_ID': submodule_id,
                'Queue_ID': queue_id,
                'Number of Instances': count,
                'Operation_Status': operation_status,
                'Epoch_Time_Human': timestamp_human,
                'Attitude_Estimation_Mode': attitude_estimation_mode,
                'Control_Mode': control_mode
            })
            
        except Exception as e:
            print(f"[ERROR] Failed parsing ADCS_CURRENT_STATE segment {idx}: {e}")
            continue
            
    return segments