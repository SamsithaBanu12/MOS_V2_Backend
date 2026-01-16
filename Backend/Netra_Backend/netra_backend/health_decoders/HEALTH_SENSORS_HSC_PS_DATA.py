import struct
from datetime import datetime

def HEALTH_SENSORS_HSC_PS_DATA(hex_str):
    header_skip_len = 29  # metadata header in bytes
    tc_len = struct.unpack('<H', bytes.fromhex(hex_str[46:50]))[0]
    tm_len = tc_len * 2 - 8
    submodule_id = int(hex_str[50:52], 16)
    queue_id = int(hex_str[52:54], 16)
    count_offset = (header_skip_len - 2) * 2

    count = struct.unpack('<H', bytes.fromhex(hex_str[count_offset:count_offset + 4]))[0]
    if count == 0:
        print("[WARN] Sensor count is zero. Skipping parsing.")
        return []

    segment_len_bytes = 20
    segment_len_hex = segment_len_bytes * 2
    
    # Payload usually starts at index 60 in these hex strings (byte offset 30)
    data_payload = hex_str[60:60 + count * segment_len_hex]

    segments = []
    for idx in range(count):
        seg = data_payload[idx * segment_len_hex:(idx + 1) * segment_len_hex]
        if len(seg) < segment_len_hex:
            continue
        
        try:
            # vbus_voltage(f), vshunt_voltage(f), current(f), power(I), psm_epoch_time(I)
            vbus_v, vshunt_v, curr, pwr, epoch_ti = struct.unpack('<fffII', bytes.fromhex(seg))
            
            # Convert epoch integer to human-readable format
            timestamp = datetime.utcfromtimestamp(epoch_ti).strftime('%Y-%m-%d %H:%M:%S')
            
        except Exception as e:
            print(f"Error unpacking HSC_PS data segment {idx}: {e}")
            continue

        segments.append({
            'Submodule_ID': submodule_id,
            'Queue_ID': queue_id,
            'Number of Instances': count,
            'Vbus_Voltage': vbus_v,
            'Vshunt_Voltage': vshunt_v,
            'Current': curr,
            'Power': pwr,
            'Timestamp': timestamp,
        })
    return segments
