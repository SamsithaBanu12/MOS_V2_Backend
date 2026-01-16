import struct
from datetime import datetime


def HEALTH_ADCS_EST_ATTITUDE_ANGLE(hex_str):
    # Standard header is 26 bytes. Payload starts at byte 26.
    # Payload header (Submodule, Queue, NumInstance) is 4 bytes.
    # Total skip to start of segments is 26 + 4 = 30 bytes.
    header_skip_len = 30
    
    # TM_LEN is at bytes 24-25 (indices 48:52)
    tm_len_raw = struct.unpack('<H', bytes.fromhex(hex_str[48:52]))[0]

    submodule_id = int(hex_str[52:54], 16) # Byte 26
    queue_id = int(hex_str[54:56], 16)     # Byte 27
    
    # count_offset is for NUM_INSTANCE at bytes 28-29 (indices 56:60)
    count_offset = 56
    count = struct.unpack('<H', bytes.fromhex(hex_str[count_offset:count_offset + 4]))[0]
    
    if count == 0:
        print("[WARN] Sensor count is zero. Skipping parsing.")
        return []

    segment_len1 = 74 # 37 bytes per segment
    data_payload = hex_str[60:] # Data starts at byte 30 (index 60)
    offset=0
    segments = []
    for idx in range(count):
        seg = data_payload[idx * segment_len1:(idx + 1) * segment_len1]
        if len(seg) < segment_len1:
           continue
        
        # Reset offset for each segment
        offset = 0
        
        # Operation Status: 1 byte (2 hex chars)
        operation_status = int(seg[offset:offset+2], 16)
        offset += 2
        
        # Epoch Time: 4 bytes (8 hex chars) - UINT (assuming Little Endian per spec usually, or matching prior logic)
        # Spec says 'UINT', previous code used '<I'.
        epoch_bytes = bytes.fromhex(seg[offset:offset+8])
        epoch_time = struct.unpack('<I', epoch_bytes)[0]
        epoch_time_human = datetime.utcfromtimestamp(epoch_time).strftime('%Y-%m-%d %H:%M:%S')
        offset += 8
        
        # Estimated Quaternion 1: 8 bytes (16 hex chars) - DOUBLE
        est_attitude_angle_1 = struct.unpack('<d', bytes.fromhex(seg[offset:offset+16]))[0]
        offset += 16
        
        # Estimated Quaternion 2: 8 bytes (16 hex chars) - DOUBLE
        est_attitude_angle_2 = struct.unpack('<d', bytes.fromhex(seg[offset:offset+16]))[0]
        offset += 16
        
        # Estimated Quaternion 3: 8 bytes (16 hex chars) - DOUBLE
        est_attitude_angle_3 = struct.unpack('<d', bytes.fromhex(seg[offset:offset+16]))[0]
        offset += 16
        
        # Estimated Quaternion 4: 8 bytes (16 hex chars) - DOUBLE
        est_attitude_angle_4 = struct.unpack('<d', bytes.fromhex(seg[offset:offset+16]))[0]
        offset += 16

        segments.append({
            'Submodule_ID':           submodule_id,
            'Queue_ID':               queue_id,
            'Number of Instances':    count,
            'Operation_Status':       operation_status,
            'Epoch_Time_Human':       epoch_time_human,
            'Est_quaternion_1':       est_attitude_angle_1,
            'Est_quaternion_2':       est_attitude_angle_2,
            'Est_quaternion_3':       est_attitude_angle_3,
            'Est_quaternion_4':       est_attitude_angle_4
        })
    return segments

hex_string = "8cc57f00a5aaf0a2c260690d0000008100046d020101ffff2c010115080000dfc26069b7f9a2e4a5a0ca3f4e3805436733d0bf43953cccce6ae93f2057e39f2b5fe03f00eac26069136b637fe848ce3f2f9e5326bb5dd1bf7fda3140652ee93f2c382bbe7b09e03f00f4c26069f591e283a1f5d03f11d68fe50e7fd2bfa810927c5aeae83f41cf73ffe95adf3f0001c3606909fc07af6223d33ff9183f9ca6d0d3bf11c70647d38de83f040567bb056cde3f000bc360699809ec5557ead43fe420bbe7cddcd4bf9f81d5b43239e83f6a253da4c999dd3f0016c360697d6893810babd63f5ef9574fe0dfd5bffd58beb7b4dde73f058e55616bbadc3f0020c3606977b18cb42465d83f32bbe7f363d9d6bfed483c73eb7ae73fc6a0417af2cfdb3f002ac36069d14f731da30fda3f86c650a4b4c4d7bf3773e0862c13e73f8c14c5091edfda3f9056ee67abbae9736c7c2ccfe48cfdaca404a54ab9fb05504c4beb374535edb6a4ba"

print(HEALTH_ADCS_EST_ATTITUDE_ANGLE(hex_string))