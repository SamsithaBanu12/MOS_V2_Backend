import struct
from datetime import datetime

# ---------------------------------------------------------
# Table 9 – EPS sub-system enum ID (subset, plus a few more for completeness)
# ---------------------------------------------------------
EPS_SUBSYSTEM_ENUM = {
    0:  "Hold and Release Module",
    1:  "Primary On-Board Controller",
    2:  "Secondary On-Board Controller",
    3:  "Primary Payload Server",
    4:  "Secondary Payload Server",
    5:  "Primary GPS",
    6:  "Secondary GPS",
    7:  "Primary ADCS",
    8:  "Reserved",
    9:  "Primary UHF",
    10: "Reserved",
    11: "Primary S-BAND",
    12: "Reserved",
    13: "Primary X-BAND",
    14: "Secondary X-BAND",
    15: "Primary Edge Server",
    16: "Secondary Edge Server",
    17: "Primary Thruster",
    18: "Reserved",
    19: "MSI",
    20: "SES - A",
    21: "SES - B",
    22: "SAS - A",
    23: "Burn Wire - 1",
    24: "SAS - B",
    25: "Burn Wire - 2",
    26: "Avionics",
    27: "Reserved",
    28: "Reserved",
}


# ---------------------------------------------------------
# Small helpers
# ---------------------------------------------------------

def _read_u8(s, pos):
    return int(s[pos:pos+2], 16), pos + 2

def _read_u16(s, pos):
    return struct.unpack('<H', bytes.fromhex(s[pos:pos+4]))[0], pos + 4

def _read_u64(s, pos):
    return struct.unpack('<Q', bytes.fromhex(s[pos:pos+16]))[0], pos + 16


# ---------------------------------------------------------
# Main parser for EPS_GET_SES_TEMP_HM (Queue ID = 1)
# ---------------------------------------------------------

def HEALTH_EPS_GET_SES_TEMP_HM(hex_str):
    """
    Parse EPS_GET_SES_TEMP_HM (Queue ID = 1) health TM from hex string.

    Table 13 layout (relative to EPS payload):
        Offset 0 : Uint8  Submodule ID
        Offset 1 : Uint8  Queue ID (must be 1)
        Offset 2 : Uint16 Number of instances
        Offset 4 : Uint64 Epoch Time
        Offset 12: Uint8  SES-A Sub-system ID (should be 20)
        Offset 13: Uint8  SES-A Temperature (255 => invalid)
        Offset 14: Uint8  SES-B Sub-system ID (should be 21)
        Offset 15: Uint8  SES-B Temperature (255 => invalid)

    Assumptions (same framing as your ADCS/EPS Live parser):
        * Submodule ID is at byte 25 (hex index 50)
        * Queue ID      is at byte 26 (hex index 52)
        * Number of instances at bytes 27–28 (hex index 54–57)
        * Epoch & SES fields repeat per instance (16 bytes per instance)
    """

    header_skip_len = 29  # bytes, up to and including "Number of instances"
    # tc_len / tm_len kept for symmetry with other decoders, but not used here
    tc_len = struct.unpack('<H', bytes.fromhex(hex_str[46:50]))[0]
    tm_len = tc_len * 2 - 8  # noqa: F841 (if unused, just informational)

    # Submodule / Queue ID
    submodule_id = int(hex_str[50:52], 16)
    queue_id = int(hex_str[52:54], 16)

    # Number of instances (Uint16_t) at bytes 27–28
    count_offset = (header_skip_len - 2) * 2  # 27 * 2 = 54
    instance_count = struct.unpack(
        '<H', bytes.fromhex(hex_str[count_offset:count_offset + 4])
    )[0]

    if instance_count == 0:
        print("[WARN] EPS_GET_SES_TEMP_HM instance count is zero. Skipping parsing.")
        return []

    segments = []

    # EPS payload base: offset 0 (Submodule ID) is at byte 25.
    # Fields we care about start from offset 4 (epoch time).
    # So starting byte = 25 + 4 = 29  -> hex index 58.
    pos = (25 + 4) * 2

    for inst_idx in range(instance_count):
        seg = {
            "Submodule_ID": submodule_id,
            "Queue_ID": queue_id,
            "Instance_Index": inst_idx,
            "Number_of_Instances": instance_count,
        }

        # 4–11: Epoch Time (Uint64_t)
        epoch_raw, pos = _read_u64(hex_str, pos)
        seg["Epoch_Time_Raw"] = epoch_raw
        try:
            seg["Epoch_Time_Human"] = datetime.utcfromtimestamp(epoch_raw).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        except (OverflowError, OSError, ValueError):
            seg["Epoch_Time_Human"] = None

        # 12: SES-A Sub-system ID
        ses_a_id, pos = _read_u8(hex_str, pos)
        seg["SES_A_Subsystem_ID"] = ses_a_id
        seg["SES_A_Subsystem_Name"] = EPS_SUBSYSTEM_ENUM.get(
            ses_a_id, f"Unknown/Reserved_{ses_a_id}"
        )

        # 13: SES-A Temperature
        ses_a_temp_raw, pos = _read_u8(hex_str, pos)
        if ses_a_temp_raw == 0xFF:
            seg["SES_A_Temperature_Valid"] = False
            seg["SES_A_Temperature_Raw"] = ses_a_temp_raw
            seg["SES_A_Temperature_degC"] = None
        else:
            # Treat as signed 8-bit (common pattern in other temp fields)
            ses_a_temp_degC = struct.unpack(
                "<b", bytes([ses_a_temp_raw])
            )[0]
            seg["SES_A_Temperature_Valid"] = True
            seg["SES_A_Temperature_Raw"] = ses_a_temp_raw
            seg["SES_A_Temperature_degC"] = ses_a_temp_degC

        # 14: SES-B Sub-system ID
        ses_b_id, pos = _read_u8(hex_str, pos)
        seg["SES_B_Subsystem_ID"] = ses_b_id
        seg["SES_B_Subsystem_Name"] = EPS_SUBSYSTEM_ENUM.get(
            ses_b_id, f"Unknown/Reserved_{ses_b_id}"
        )

        # 15: SES-B Temperature
        ses_b_temp_raw, pos = _read_u8(hex_str, pos)
        if ses_b_temp_raw == 0xFF:
            seg["SES_B_Temperature_Valid"] = False
            seg["SES_B_Temperature_Raw"] = ses_b_temp_raw
            seg["SES_B_Temperature_degC"] = None
        else:
            ses_b_temp_degC = struct.unpack(
                "<b", bytes([ses_b_temp_raw])
            )[0]
            seg["SES_B_Temperature_Valid"] = True
            seg["SES_B_Temperature_Raw"] = ses_b_temp_raw
            seg["SES_B_Temperature_degC"] = ses_b_temp_degC

        segments.append(seg)

    return segments
