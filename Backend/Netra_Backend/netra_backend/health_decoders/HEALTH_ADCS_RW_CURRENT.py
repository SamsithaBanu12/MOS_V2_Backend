import struct 
from datetime import datetime
def HEALTH_ADCS_RW_CURRENT(hex_str):
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

    segment_len = 28
    data_payload = hex_str[60:60+count * segment_len]
    segments = []
    for idx in range(count):
        seg = data_payload[idx * segment_len:(idx + 1) * segment_len]
        if len(seg) < segment_len:
            continue

        # ---- Fixed fields ----
        operation_status = int(seg[0:2], 16)

        epoch_bytes = bytes.fromhex(seg[2:10])
        epoch_time = struct.unpack('<I', epoch_bytes)[0]
        epoch_time_human = datetime.utcfromtimestamp(epoch_time).strftime('%Y-%m-%d %H:%M:%S')

        Number_of_reaction_wheel = int(seg[10:12], 16)

        # ---- Reaction wheel currents (explicit n=3 / n=4) ----
        if Number_of_reaction_wheel == 3:
            Reaction_wheel_current_1 = struct.unpack('<H', bytes.fromhex(seg[12:16]))[0] * 0.1
            Reaction_wheel_current_2 = struct.unpack('<H', bytes.fromhex(seg[16:20]))[0] * 0.1
            Reaction_wheel_current_3 = struct.unpack('<H', bytes.fromhex(seg[20:24]))[0] * 0.1

            Reaction_wheel_current_4 = None  # not present

        elif Number_of_reaction_wheel == 4:
            Reaction_wheel_current_1 = struct.unpack('<H', bytes.fromhex(seg[12:16]))[0] * 0.1
            Reaction_wheel_current_2 = struct.unpack('<H', bytes.fromhex(seg[16:20]))[0] * 0.1
            Reaction_wheel_current_3 = struct.unpack('<H', bytes.fromhex(seg[20:24]))[0] * 0.1
            Reaction_wheel_current_4 = struct.unpack('<H', bytes.fromhex(seg[24:28]))[0] * 0.1

        else:
            print(f"[WARN] Invalid reaction wheel count: {Number_of_reaction_wheel}")
            continue

        # ---- Store parsed segment ----
        segments.append({
            'Submodule_ID': submodule_id,
            'Queue_ID': queue_id,
            'Number of Instances': count,
            'Operation_Status': operation_status,
            'Epoch_Time_Human': epoch_time_human,
            'Number_of_reaction_wheel': Number_of_reaction_wheel,
            'Reaction_wheel_current_1': Reaction_wheel_current_1,
            'Reaction_wheel_current_2': Reaction_wheel_current_2,
            'Reaction_wheel_current_3': Reaction_wheel_current_3,
            'Reaction_wheel_current_4': Reaction_wheel_current_4,
        })

    return segments
