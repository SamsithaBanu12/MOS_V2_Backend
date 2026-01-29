import re
import struct
from datetime import datetime
from typing import Dict, List, Any, Tuple

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = None


DECODE_SOLAR_PANEL_COUNT = 9
DECODE_SOLAR_TEMP_COUNT = 5
DECODE_OUTPUT_CONV_COUNT = 5
DECODE_BATT_TEMP_COUNT = 24
DECODE_PS_CHANNEL_COUNT = 52

RESERVED_AFTER_PAYLOAD_BYTES = 90

EXPECTED_PAYLOAD_BYTES_FIXED = (
    8 + 8 + 18 + 18 + 5 + 10 + 2 + 2 + 24 + 7 + 104 + 7 + 1
)

VALID_SUBSYSTEMS_22 = [
    "HRM", "OBC", "OBC2", "PL_SERVER", "PL_SERVER_2", "GPS", "GPS_2", "ADCS",
    "UHF", "S_BAND", "X_BAND", "X_BAND_2", "EDGE", "EDGE_2", "THRUSTER", "MSI",
    "SES_A", "SES_B", "SAS_A", "UHF_BURN_WIRE", "SAS_B", "AVIONICS",
]

BATTERY_MODES = {0: "OFF", 1: "Critical", 2: "Safe", 3: "Normal", 4: "Full"}


# ----------------------------
# MAPPINGS (for named columns)
# ----------------------------

ACTIVE_HW_32 = {
    0: "SAS_B",
    1: "Burn Wire 2",
    2: "Avionics",
    3: "Reserved",
    4: "Reserved",
    5: "Reserved",
    6: "Reserved",
    7: "Reserved",
    8: "Secondary Edge Server",
    9: "Primary Thruster",
    10: "Reserved",
    11: "MSI",
    12: "SES - A",
    13: "SES - B",
    14: "SAS - A",
    15: "Burn Wire - 1",
    16: "Reserved",
    17: "Primary UHF",
    18: "Reserved",
    19: "Primary S-BAND",
    20: "Reserved",
    21: "Primary X-BAND",
    22: "Secondary X-BAND",
    23: "Primary Edge Server",
    24: "Hold and Release Module",
    25: "Primary On - Board Controller",
    26: "Secondary On - Board Controller",
    27: "Primary Payload Server",
    28: "Secondary Payload Server",
    29: "Primary GPS",
    30: "Secondary GPS",
    31: "Primary ADCS",
}

BITNUM_TO_CHANNEL: Dict[int, str] = {
    15: "HRM 15",
    16: "HRM 16",
    17: "HRM 17",
    18: "HRM 18",
    19: "HRM 19",
    20: "HRM 20",
    21: "HRM 21",
    22: "HRM 22",
    0: "OBC 00",
    1: "OBC 01",
    3: "ADCS 03",
    7: "UHF 07",
    8: "SBAND 08",
    10: "XBAND 10",
    9: "XBAND_2 09",
    4: "THRUSTER 04",
    5: "THRUSTER 05",
    6: "THRUSTER (Heater) 06",
    11: "PL_1 11",
    13: "PL_2 13",
    12: "PL_2 (Heater) 12 / PL_3 (Heater) 12",
    14: "PL_3 14",
    23: "PL_4 23",
    24: "PL_4 (Heater) 24",
    25: "PL_5 25",
    49: "PL_6 49",
    50: "PL_6 (Heater) 50",
    51: "PL_7 51",
    2: "PL_8 02",
}

PORT_TO_CH: Dict[int, str] = {}
def _add_port(ch_name: str, primary: int | None, redundant: int | None):
    if primary is not None:
        PORT_TO_CH[primary] = ch_name
    if redundant is not None:
        PORT_TO_CH[redundant] = ch_name

_add_port("HRM 15", 15, 41)
_add_port("HRM 16", 16, 42)
_add_port("HRM 17", 17, 43)
_add_port("HRM 18", 18, 44)
_add_port("HRM 19", 19, 45)
_add_port("HRM 20", 20, 46)
_add_port("HRM 21", 21, 47)
_add_port("HRM 22", 22, 48)
_add_port("OBC 00", 0, 26)
_add_port("OBC 01", 1, 27)
_add_port("ADCS 03", 3, 29)
_add_port("UHF 07", 7, 33)
_add_port("SBAND 08", 8, 34)
_add_port("XBAND 10", 10, 36)
_add_port("XBAND_2 09", 9, 35)
_add_port("THRUSTER 04", 4, 30)
_add_port("THRUSTER 05", 5, 31)
_add_port("THRUSTER (Heater) 06", 6, 32)
_add_port("PL_1 11", 11, 37)
_add_port("PL_2 13", 13, 39)
_add_port("PL_2 (Heater) / PL_3 (Heater)", 12, 38)
_add_port("PL_3 14", 14, 40)
_add_port("PL_4 23", 23, None)
_add_port("PL_4 (Heater) 24", 24, None)
_add_port("PL_5 25", 25, None)
_add_port("PL_6 49", 49, None)
_add_port("PL_6 (Heater) 50", 50, None)
_add_port("PL_7 51", 51, None)
_add_port("PL_8 02", 2, 28)


# ----------------------------
# Column-name helpers
# ----------------------------

def _colify(name: str) -> str:
    """
    Turn 'Primary On - Board Controller' -> 'PRIMARY_ON_BOARD_CONTROLLER'
    Keeps only [A-Z0-9_]
    """
    if name is None:
        return "UNKNOWN"
    s = name.upper()
    s = s.replace("&", "AND")
    s = re.sub(r"[^A-Z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return (s or "UNKNOWN")[:60]

def _active_hw_col(i: int) -> str:
    hw_name = ACTIVE_HW_32.get(i, f"UNKNOWN_{i}")
    # index suffix keeps duplicates like RESERVED unique
    return f"Active_HW_{_colify(hw_name)}_{i:02d}"

def _ps_name_for_bit(i: int) -> str:
    return BITNUM_TO_CHANNEL.get(i, "Redundant")

def _ps_name_for_port(i: int) -> str:
    return PORT_TO_CH.get(i, BITNUM_TO_CHANNEL.get(i, "Redundant"))

def _ps_onoff_col(i: int) -> str:
    return f"PS_OnOff_{_colify(_ps_name_for_bit(i))}_{i:02d}"

def _ps_overcurrent_col(i: int) -> str:
    return f"PS_Overcurrent_{_colify(_ps_name_for_bit(i))}_{i:02d}"

def _ps_current_col(i: int) -> str:
    return f"PS_Current_A_{_colify(_ps_name_for_port(i))}_{i:02d}"


# ----------------------------
# Byte helpers
# ----------------------------

def _clean_hex_string(hex_str: str) -> bytes:
    s = hex_str.replace('"', "").replace("'", "").replace(",", " ").replace("\n", " ").replace("\t", " ")
    s = "".join(s.split())
    if len(s) % 2 != 0:
        raise ValueError("Hex string has odd length after cleaning.")
    return bytes.fromhex(s)

def _need(buf: bytes, pos: int, n: int, where: str):
    if pos + n > len(buf):
        raise ValueError(f"Not enough bytes while reading {where}: need {n}, have {len(buf)-pos} (pos={pos})")

def _need_payload(pos: int, n: int, payload_end: int, where: str):
    if pos + n > payload_end:
        raise ValueError(f"Not enough PAYLOAD bytes while reading {where}: need {n}, have {payload_end - pos} (pos={pos})")

def _u8(buf: bytes, pos: int, where="u8") -> Tuple[int, int]:
    _need(buf, pos, 1, where)
    return buf[pos], pos + 1

def _i8(buf: bytes, pos: int, where="i8") -> Tuple[int, int]:
    _need(buf, pos, 1, where)
    return struct.unpack("<b", buf[pos:pos+1])[0], pos + 1

def _u16le(buf: bytes, pos: int, where="u16le") -> Tuple[int, int]:
    _need(buf, pos, 2, where)
    return int.from_bytes(buf[pos:pos+2], "little", signed=False), pos + 2

def _i16le(buf: bytes, pos: int, where="i16le") -> Tuple[int, int]:
    _need(buf, pos, 2, where)
    return int.from_bytes(buf[pos:pos+2], "little", signed=True), pos + 2

def _u32le(buf: bytes, pos: int, where="u32le") -> Tuple[int, int]:
    _need(buf, pos, 4, where)
    return int.from_bytes(buf[pos:pos+4], "little", signed=False), pos + 4

def _u32raw(buf: bytes, pos: int, where="u32raw") -> Tuple[bytes, int]:
    _need(buf, pos, 4, where)
    return buf[pos:pos+4], pos + 4

def _fmt_ist(ts: int) -> str:
    """
    Format timestamp to IST string. Handles timestamps in seconds, milliseconds, or microseconds.
    Falls back to raw value string if conversion fails.
    """
    # Validate and convert timestamp
    # Unix timestamps in seconds should be reasonable (e.g., between 2000-2100)
    # 946684800 = Jan 1, 2000
    # 4102444800 = Jan 1, 2100
    
    original_ts = ts
    
    # If timestamp is too large, it's likely in milliseconds or microseconds
    if ts > 4102444800:
        # Try milliseconds (divide by 1000)
        if ts > 4102444800000:
            # Likely microseconds (divide by 1000000)
            ts = ts // 1000000
        else:
            # Likely milliseconds (divide by 1000)
            ts = ts // 1000
    
    # If still unreasonable, return raw value
    if ts < 0 or ts > 4102444800:
        return f"INVALID_TS({original_ts})"
    
    try:
        if IST is not None:
            dt = datetime.fromtimestamp(ts, tz=IST)
        else:
            dt = datetime.fromtimestamp(ts)
        s = dt.strftime("%B %d, %Y %I:%M:%S %p")
        s = s.replace(" 0", " ")
        return s
    except (OSError, ValueError, OverflowError) as e:
        # If conversion still fails, return raw value
        return f"INVALID_TS({original_ts})"


# ----------------------------
# Main decoder (named columns)
# ----------------------------

def HEALTH_EPS(hex_str: str) -> List[Dict[str, Any]]:
    buf = _clean_hex_string(hex_str)
    pos = 0

    # Skip first 26 bytes (your EPS format)
    _need(buf, pos, 26, "skip header 26 bytes")
    pos += 26

    submodule_id, pos = _u8(buf, pos, "Submodule ID")
    queue_id, pos = _u8(buf, pos, "Queue ID")
    count, pos = _u16le(buf, pos, "Number of Instances")

    if count == 0:
        return []

    segments: List[Dict[str, Any]] = []

    def _base_segment() -> Dict[str, Any]:
        seg: Dict[str, Any] = {
            "Submodule_ID": submodule_id,
            "Queue_ID": queue_id,
            "Number_of_Instances": count,
        }

        # Active HW bits (32 named bool columns)
        for i in range(32):
            seg[_active_hw_col(i)] = None

        # Valid subsystems (22 ON/OFF columns)
        seg["Valid_Subsystems_Count"] = None
        for name in VALID_SUBSYSTEMS_22:
            seg[f"Valid_{name}"] = None

        seg.update({
            "Timestamp": None,
            "Epoch_Time": None,
            "Epoch_Time_Human": None,
            "Power_Generated_Last_Orbit_Wh": None,
            "Power_Consumed_Last_Orbit_Wh": None,
            "Total_Power_Generated_Wh": None,
            "Total_Power_Consumed_Wh": None,
            "Reserved_After_Valid_Status_U16": None,
            "Payload_Length_Bytes": None,

            "Solar_Panel_Count": None,
            "Solar_Temp_Sensor_Count": None,
            "MPPT_Count": None,
            "Output_Converter_Count": None,
            "Payload_Reserved1": None,
            "Battery_Count": None,
            "Battery_Temp_Sensor_Count": None,
            "Power_Supply_Channel_Count": None,

            "OBC_Reset_Count": None,
            "Output_Channel_Reset_Count": None,

            "Battery_Total_Voltage_V": None,
            "Battery_Total_Current_A": None,

            "Battery_Mode": None,
            "Primary_HDRM_Release": None,
            "Secondary_HDRM_Release": None,
            "UHF_Antenna_Release": None,

            "Payload_Align_Skip_Bytes": None,
            "Parse_Error": None,
        })

        for i in range(DECODE_SOLAR_PANEL_COUNT):
            seg[f"Solar_Panel_Voltage_V_{i+1:02d}"] = None
            seg[f"Solar_Panel_Current_A_{i+1:02d}"] = None
        for i in range(DECODE_SOLAR_TEMP_COUNT):
            seg[f"Solar_Temp_C_{i+1:02d}"] = None
        for i in range(DECODE_OUTPUT_CONV_COUNT):
            seg[f"Output_Converter_Voltage_V_{i+1:02d}"] = None
        for i in range(DECODE_BATT_TEMP_COUNT):
            seg[f"Battery_Temp_C_{i+1:02d}"] = None

        # PS bitmaps/currents -> named columns
        for i in range(DECODE_PS_CHANNEL_COUNT):
            seg[_ps_onoff_col(i)] = None
            seg[_ps_current_col(i)] = None
            seg[_ps_overcurrent_col(i)] = None

        return seg

    for inst_idx in range(count):
        seg = _base_segment()

        # ---- Prefix ----
        ts, pos = _u32le(buf, pos, "Timestamp")

        # Normalize timestamp (handle ms/us)
        norm_ts = ts
        if norm_ts > 4102444800:
            if norm_ts > 4102444800000:
                norm_ts //= 1000000
            else:
                norm_ts //= 1000

        seg["Epoch_Time"] = int(norm_ts)
        try:
            seg["Epoch_Time_Human"] = datetime.utcfromtimestamp(norm_ts).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            seg["Epoch_Time_Human"] = None

        seg["Timestamp"] = _fmt_ist(ts)

        pg_last, pos = _u32le(buf, pos, "Power Generated Last Orbit")
        seg["Power_Generated_Last_Orbit_Wh"] = pg_last / 100.0

        pc_last, pos = _u32le(buf, pos, "Power Consumed Last Orbit")
        seg["Power_Consumed_Last_Orbit_Wh"] = pc_last / 100.0

        pgt, pos = _u32le(buf, pos, "Total Power Generated")
        seg["Total_Power_Generated_Wh"] = pgt / 100.0

        pct, pos = _u32le(buf, pos, "Total Power Consumed")
        seg["Total_Power_Consumed_Wh"] = pct / 100.0

        # Active HW status -> named
        active4, pos = _u32raw(buf, pos, "Active Channel HW Status (4 bytes)")
        for i in range(32):
            byte_i = i // 8
            bit_i = i % 8
            seg[_active_hw_col(i)] = bool((active4[byte_i] >> bit_i) & 1)

        valid_n, pos = _u8(buf, pos, "Total valid subsystems")
        seg["Valid_Subsystems_Count"] = valid_n

        for i, name in enumerate(VALID_SUBSYSTEMS_22):
            if i < valid_n:
                st, pos = _u8(buf, pos, f"Valid subsystem status[{i}]")
                seg[f"Valid_{name}"] = "ON" if st == 1 else "OFF"
            else:
                seg[f"Valid_{name}"] = None

        reserved2, pos = _u16le(buf, pos, "Reserved (2 bytes)")
        seg["Reserved_After_Valid_Status_U16"] = reserved2

        payload_len, pos = _u16le(buf, pos, "Payload Length")
        seg["Payload_Length_Bytes"] = payload_len

        payload_start = pos
        payload_end = payload_start + payload_len

        if payload_end > len(buf):
            seg["Parse_Error"] = f"Payload length {payload_len} exceeds remaining bytes."
            segments.append(seg)
            break

        if payload_len < EXPECTED_PAYLOAD_BYTES_FIXED:
            seg["Parse_Error"] = (
                f"Payload too short: payload_len={payload_len}, "
                f"expected_at_least={EXPECTED_PAYLOAD_BYTES_FIXED}"
            )
            pos = payload_end
            if inst_idx < count - 1 and pos + RESERVED_AFTER_PAYLOAD_BYTES <= len(buf):
                pos += RESERVED_AFTER_PAYLOAD_BYTES
            segments.append(seg)
            continue

        # ---- Payload counts ----
        _need_payload(pos, 8, payload_end, "Count bytes block (8 bytes)")
        seg["Solar_Panel_Count"], pos = _u8(buf, pos, "Solar panel count (raw)")
        seg["Solar_Temp_Sensor_Count"], pos = _u8(buf, pos, "Solar temp sensor count (raw)")
        seg["MPPT_Count"], pos = _u8(buf, pos, "MPPT count (raw)")
        seg["Output_Converter_Count"], pos = _u8(buf, pos, "Output converter count (raw)")
        seg["Payload_Reserved1"], pos = _u8(buf, pos, "Payload reserved (1 byte)")
        seg["Battery_Count"], pos = _u8(buf, pos, "Battery count (raw)")
        seg["Battery_Temp_Sensor_Count"], pos = _u8(buf, pos, "Battery temp sensor count (raw)")
        seg["Power_Supply_Channel_Count"], pos = _u8(buf, pos, "Power supply channel count (raw)")

        seg["OBC_Reset_Count"], pos = _u32le(buf, pos, "OBC Reset Count")
        seg["Output_Channel_Reset_Count"], pos = _u32le(buf, pos, "Output Channel Reset Count")

        # Solar panel voltages (9 * 2), /10 V
        _need_payload(pos, DECODE_SOLAR_PANEL_COUNT * 2, payload_end, "Solar panel voltages")
        for i in range(DECODE_SOLAR_PANEL_COUNT):
            raw, pos = _u16le(buf, pos, f"Solar voltage[{i}]")
            seg[f"Solar_Panel_Voltage_V_{i+1:02d}"] = raw / 10.0

        # Solar panel currents (9 * 2), /100 A
        _need_payload(pos, DECODE_SOLAR_PANEL_COUNT * 2, payload_end, "Solar panel currents")
        for i in range(DECODE_SOLAR_PANEL_COUNT):
            raw, pos = _u16le(buf, pos, f"Solar current[{i}]")
            seg[f"Solar_Panel_Current_A_{i+1:02d}"] = raw / 100.0

        # Solar temps (5 * 1)
        _need_payload(pos, DECODE_SOLAR_TEMP_COUNT, payload_end, "Solar temp sensors")
        for i in range(DECODE_SOLAR_TEMP_COUNT):
            t, pos = _i8(buf, pos, f"Solar temp[{i}]")
            seg[f"Solar_Temp_C_{i+1:02d}"] = t

        # Output converter voltages (5 * 2), /10 V
        _need_payload(pos, DECODE_OUTPUT_CONV_COUNT * 2, payload_end, "Output converter voltages")
        for i in range(DECODE_OUTPUT_CONV_COUNT):
            raw, pos = _u16le(buf, pos, f"Output converter voltage[{i}]")
            seg[f"Output_Converter_Voltage_V_{i+1:02d}"] = raw / 10.0

        # Battery total voltage (2), /10 V
        _need_payload(pos, 2, payload_end, "Total battery voltage")
        batt_v_raw, pos = _u16le(buf, pos, "Total battery voltage")
        seg["Battery_Total_Voltage_V"] = batt_v_raw / 10.0

        # Battery total current (2), /100 A
        _need_payload(pos, 2, payload_end, "Total battery current")
        batt_i_raw, pos = _i16le(buf, pos, "Total battery current")
        seg["Battery_Total_Current_A"] = batt_i_raw / 100.0

        # Battery temps (24 * 1)
        _need_payload(pos, DECODE_BATT_TEMP_COUNT, payload_end, "Battery temp sensors")
        for i in range(DECODE_BATT_TEMP_COUNT):
            t, pos = _i8(buf, pos, f"Battery temp[{i}]")
            seg[f"Battery_Temp_C_{i+1:02d}"] = t

        # ON/OFF bitmap (7 bytes) -> named ON/OFF columns
        _need_payload(pos, 7, payload_end, "Power supply ON/OFF bitmap (7 bytes)")
        onoff7 = buf[pos:pos+7]
        pos += 7
        for i in range(DECODE_PS_CHANNEL_COUNT):
            byte_i = i // 8
            bit_i = i % 8
            bit_val = (onoff7[byte_i] >> bit_i) & 1
            seg[_ps_onoff_col(i)] = "ON" if bit_val else "OFF"

        # PS currents (52 * 2): divide by 100 A -> named columns
        _need_payload(pos, DECODE_PS_CHANNEL_COUNT * 2, payload_end, "PS channel currents (52*2 bytes)")
        for i in range(DECODE_PS_CHANNEL_COUNT):
            raw, pos = _u16le(buf, pos, f"PS channel current[{i}]")
            seg[_ps_current_col(i)] = raw / 100.0

        # Overcurrent bitmap (7 bytes) -> named boolean columns
        _need_payload(pos, 7, payload_end, "Overcurrent bitmap (7 bytes)")
        oc7 = buf[pos:pos+7]
        pos += 7
        for i in range(DECODE_PS_CHANNEL_COUNT):
            byte_i = i // 8
            bit_i = i % 8
            seg[_ps_overcurrent_col(i)] = bool((oc7[byte_i] >> bit_i) & 1)

        # HRM status byte -> battery mode + releases
        _need_payload(pos, 1, payload_end, "HRM status byte")
        hrm_status, pos = _u8(buf, pos, "HRM status byte")

        seg["Battery_Mode"] = BATTERY_MODES.get(hrm_status & 0b00000111, f"Unknown({hrm_status & 7})")
        seg["Primary_HDRM_Release"] = bool((hrm_status >> 5) & 1)
        seg["Secondary_HDRM_Release"] = bool((hrm_status >> 6) & 1)
        seg["UHF_Antenna_Release"] = bool((hrm_status >> 7) & 1)

        # Align to payload_end (scalar)
        if pos != payload_end:
            seg["Payload_Align_Skip_Bytes"] = int(payload_end - pos) if payload_end > pos else 0
            pos = payload_end

        # Reserved bytes between instances
        if inst_idx < count - 1:
            if pos + RESERVED_AFTER_PAYLOAD_BYTES <= len(buf):
                pos += RESERVED_AFTER_PAYLOAD_BYTES
            else:
                seg["Parse_Error"] = (
                    f"Missing reserved-after-payload bytes: need {RESERVED_AFTER_PAYLOAD_BYTES}, "
                    f"have {len(buf) - pos}"
                )
                segments.append(seg)
                break

        segments.append(seg)

    return segments