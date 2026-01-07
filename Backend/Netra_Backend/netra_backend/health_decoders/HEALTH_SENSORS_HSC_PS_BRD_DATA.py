def HEALTH_SENSORS_HSC_PS_BRD_DATA(hex_str):
    header_skip_len = 29  # metadata header in bytes
    tc_len=struct.unpack('<H', bytes.fromhex(hex_str[46:50]))[0]
    tm_len=tc_len*2 -8
    submodule_id = int(hex_str[50:52], 16)
    queue_id = int(hex_str[52:54], 16)
    count_offset = (header_skip_len - 2) * 2

    count = struct.unpack('<H', bytes.fromhex(hex_str[count_offset:count_offset + 4]))[0]
    if count == 0:
        print("[WARN] Sensor count is zero. Skipping parsing.")
        return []

    segment_len=tm_len//count

    segment_len1=segment_len
    data_payload = hex_str[58:58+tm_len]

    segments = []
    for idx in range(count):

        seg = data_payload[idx * segment_len1:(idx + 1) * segment_len1]
        if len(seg) < segment_len1:
           continue

        offset = 0
        try:
            vbus_voltage = struct.unpack('<f', bytes.fromhex(seg[offset:offset + 8]))[0]
            offset += 8
            vshunt_voltage = struct.unpack('<f', bytes.fromhex(seg[offset:offset + 8]))[0]
            offset += 8
            current = struct.unpack('<f', bytes.fromhex(seg[offset:offset + 8]))[0]
            offset += 8
            power = struct.unpack('<I', bytes.fromhex(seg[offset:offset + 8]))[0]
            offset += 8
            epoch_tim1= seg[offset:offset + 8]
            offset += 8
            epoch_time_reversed = ''.join([epoch_tim1[i:i + 2] for i in range(0, 8, 2)][::-1])
            epoch_ti = int(epoch_time_reversed, 16)
            # Convert epoch integer to human-readable format
            epoch_time = datetime.utcfromtimestamp(epoch_ti).strftime('%Y-%m-%d %H:%M:%S')
            
        except Exception as e:
            print(f"Error unpacking PSM data segment {idx}: {e}")
            continue


        segments.append({
            'Submodule_ID': submodule_id,
            'Queue_ID': queue_id,
            'Number of Instances': count,
            'Vbus_Voltage': vbus_voltage,
            'Vshunt_Voltage': vshunt_voltage,
            'Current': current,
            'Power': power,
            'Timestamp': epoch_time,
        })

    return segments