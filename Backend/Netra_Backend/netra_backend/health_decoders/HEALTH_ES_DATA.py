import struct
from datetime import datetime
def HEALTH_ES_DATA(hex_str):
    header_skip_len = 29  # metadata header in bytes
    tc_len=struct.unpack('<H', bytes.fromhex(hex_str[46:50]))[0]
    tm_len=tc_len*2 -8

    queue_id = int(hex_str[52:54], 16)
    count_offset = (header_skip_len - 2) * 2

    count = struct.unpack('<H', bytes.fromhex(hex_str[count_offset:count_offset + 4]))[0]
    if count == 0:
        print("[WARN] Sensor count is zero. Skipping parsing.")
        return []

    segment_len = 60
    data_payload = hex_str[60:60+count * segment_len]
    segments = []
    for idx in range(count):
        seg = data_payload[idx * segment_len:(idx + 1) * segment_len]
        if len(seg) < segment_len:
           continue
        b = seg

        # ----- Parse fields -----
        offset = 0

        submodule_id = b[offset:offset+2]
        offset += 2

        queue_id = b[offset:offset+2]
        offset += 2

        num_instance = b[offset:offset+2]
        offset += 2

        cpu_load = struct.unpack('<f', b[offset:offset+8])[0]
        offset += 8

        epoch_time = struct.unpack('<I', b[offset:offset+8])[0]
        offset += 8

        uptime = struct.unpack('<I', b[offset:offset+8])[0]
        offset += 8

        ps_temp_info = struct.unpack('<b', b[offset:offset+2])[0]
        offset += 2

        memory_util_ssd = struct.unpack('<f', b[offset:offset+8])[0]
        offset += 8

        memory_util_ram = struct.unpack('<f', b[offset:offset+8])[0]
        offset += 8
        no_ipcc_rcvd_eth = struct.unpack('<I', b[offset:offset+8])[0]
        offset += 8

        no_ipcc_rcvd_usb = struct.unpack('<I', b[offset:offset+8])[0]
        offset += 8

        no_ipcc_drop_ps = struct.unpack('<I', b[offset:offset+8])[0]
        offset += 8
        reserved_1=struct.unpack('<I', b[offset:offset+8])[0]
        offset += 8
        reserved_2=struct.unpack('<I', b[offset:offset+8])[0]
        offset += 8

        no_ipcc_sent_eth = struct.unpack('<I', b[offset:offset+8])[0]
        offset += 8

        no_ipcc_sent_usb = struct.unpack('<I', b[offset:offset+8])[0]
        offset += 8

        no_ipcc_drop_obc = struct.unpack('<I', b[offset:offset+8])[0]
        offset += 8


        segments.append({

        "QUEUE_ID": queue_id,
        "NUM_INSTANCE": num_instance,

        "CPU_LOAD": cpu_load,
        "EPOCH_TIME": epoch_time,
        "UPTIME": uptime,
        "ES_TEMP_INFO": ps_temp_info,

        "SSD_MEMORY_UTIL": memory_util_ssd,
        "RAM_MEMORY_UTIL": memory_util_ram,

        "IPCC_RECEIVED_ETH": no_ipcc_rcvd_eth,
        "IPCC_RECEIVED_USB": no_ipcc_rcvd_usb,
        "IPCC_DROPPED_ES": no_ipcc_drop_ps,

        "IPCC_SENT_ETH": no_ipcc_sent_eth,
        "IPCC_SENT_USB": no_ipcc_sent_usb,
        "IPCC_DROPPED_OBC": no_ipcc_drop_obc
        })
    return segments
