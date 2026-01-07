import struct

# From Table 106 (already used in Queue 1 typically)
# Make sure this exists once in your module.
SNS_ERR_ID_ENUM = {
    0: "INVLD_AH_INST_ID",
    1: "MCU_ID",
    2: "OBC_TEMP_SENSOR",
    3: "PS_TEMP_SENSOR",
    4: "ES_TEMP_SENSOR_1",
    5: "ES_TEMP_SENSOR_2",
    6: "GPS_TEMP_SENSOR",
    7: "NIC_TEMP_SENSOR",
    8: "PWR_TEMP_SENSOR",
    9: "PS_SSD0_TEMP_SENSOR",
    10: "PS_SSD1_TEMP_SENSOR",
    11: "PS_SSD2_TEMP_SENSOR",
    12: "PS_SSD3_TEMP_SENSOR",
    13: "ES_SSD0_TEMP_SENSOR",
    14: "ES_SSD1_TEMP_SENSOR",
    15: "SP_1_TEMP_SENSOR",
    16: "SP_2_TEMP_SENSOR",
    17: "SP_3_TEMP_SENSOR",
    18: "SP_4_TEMP_SENSOR",
    19: "SP_5_TEMP_SENSOR",
    20: "OBC_1_PSM_SENSOR",
    21: "OBC_2_PSM_SENSOR",
    22: "PS_BRD_PSM_SENSOR",
    23: "PS_1_PSM_SENSOR",
    24: "PS_2_PSM_SENSOR",
    25: "ES_1_PSM_SENSOR",
    26: "ES_2_PSM_SENSOR",
    27: "NIC_PSM_SENSOR",
    28: "PS_BRD_HSC_SENSOR",
    29: "PS_SSD_HSC_SENSOR",
    30: "PS_1_HSC_SENSOR",
    31: "PS_2_HSC_SENSOR",
    32: "ES_1_HSC_SENSOR",
    33: "ES_2_HSC_SENSOR",
    34: "NIC_HSC_SENSOR",
    35: "PS_SSD0_HEAT_COIL",
    36: "PS_SSD1_HEAT_COIL",
    37: "PS_SSD2_HEAT_COIL",
    38: "PS_SSD3_HEAT_COIL",
    39: "ES_SSD0_HEAT_COIL",
    40: "ES_SSD1_HEAT_COIL",
    41: "ADC_AD7291_PS_1",
    42: "ADC_AD7291_PS_2",
    43: "ADC_AD7291_ORING_CIRCUIT",
    44: "GPIO_EXPANDER_PCAL6408A_PS",
    45: "GPIO_EXPANDER_MCP23008_EDGE_1",
    46: "GPIO_EXPANDER_MCP23008_EDGE_2",
    47: "GPIO_EXPANDER_MCP23008_OBC_1",
    48: "GPIO_EXPANDER_MCP23008_OBC_2",
    49: "GPIO_EXPANDER_MCP23008_GPS",
    50: "GPIO_EXPANDER_PCA9673",
    51: "THRUSTER_MORPHEUS_OBC",
    52: "DATA_LOGGER_ADS7828_PS",
    53: "EXT_MEM_MX25L512_QSPI",
    54: "EXT_MEM_MT25QL512_QSPI",
    55: "EXT_MEM_S25HL512T_QSPI",
    56: "EXT_MEM_MT28EW128_FMC",
    57: "EXT_MEM_M24C16_EEPROM_1",
    58: "EXT_MEM_M24C16_EEPROM_2",
    59: "EXT_MEM_AT24C32E_EEPROM_1",
    60: "EXT_MEM_AT24C32E_EEPROM_2",
    61: "UART_EXPANDER_MAX14830_OBC",
    62: "GPIO_EXPANDER_MCP23008_EDGE_1_GEN_2",
    63: "GPIO_EXPANDER_MCP23008_EDGE_2_GEN_2",
    64: "GPIO_EXPANDER_MCP23008_EDGE_3_GEN_2",
    65: "GPIO_EXPANDER_MCP23008_EDGE_4_GEN_2",
    66: "GPIO_EXPANDER_PCAL6408A_PS_GEN2",
    67: "GPIO_EXPANDER_MCP23008_NIC_1",
    68: "GPIO_EXPANDER_MCP23008_NIC_2",
    69: "GPIO_EXPANDER_MCP23008_NIC_3",
    70: "GPIO_EXPANDER_MCP23008_SSD_1",
    71: "GPIO_EXPANDER_MCP23008_SSD_2",
    72: "GPIO_EXPANDER_MCP23008_BACK_PLANE",
    73: "GPIO_EXPANDER_MCP23008_POWER_BOARD_1",
    74: "GPIO_EXPANDER_MCP23008_POWER_BOARD_2",
    75: "GPIO_EXPANDER_MCP23008_POWER_BOARD_3",
    76: "EPS_NS",
    77: "EPS_M600",
    78: "EPS_NL",
    79: "EPS_SIM",
    80: "GNSS_HW_RECV_OEM719",
    81: "GNSS_ON_BRD_PROPAGATOR",
    82: "ADCS_CUBESPACE_GEN1",
    83: "ADCS_CUBESPACE_GEN2",
    84: "ADCS_BLUECANYON",
    85: "ADCS_SIM",
    86: "MAX_AH_INST_ID",
}

# From enum: last value 86 = MAX_AH_INST_ID
# Typically the array length is MAX_AH_INST_ID (<= 86). Use your C header for truth.
MAX_AH_INST_ID = 86


def HEALTH_FDIR_DATA_QUEUE_2(hex_str: str):
    """
    Parse TM Get Health – FDIR_DATA_QUEUE_ID (QUEUE_ID = 2).

    Per instance struct (s_fdir_sns_rst_err_info):

        typedef struct {
            uint8_t sns_hw_rst_cnt;
            uint8_t sns_hw_err_cnt;
        } s_hw_trck_t;

        typedef struct {
            s_hw_trck_t fdir_sns_hw_trck[MAX_AH_INST_ID];
        } s_fdir_sns_rst_err_info;

    So each instance is:
        2 * MAX_AH_INST_ID bytes  =>  4 * MAX_AH_INST_ID hex chars.
    """

    header_skip_len = 29  # metadata header in bytes

    # TC length (for completeness)
    tc_len = struct.unpack('<H', bytes.fromhex(hex_str[46:50]))[0]
    tm_len = tc_len * 2 - 8  # same pattern as other health functions (not used further)

    # Submodule ID and Queue ID
    submodule_id = int(hex_str[50:52], 16)
    queue_id     = int(hex_str[52:54], 16)

    # Number of instances
    count_offset = (header_skip_len - 2) * 2
    count = struct.unpack('<H', bytes.fromhex(hex_str[count_offset:count_offset + 4]))[0]

    if count == 0:
        print("[WARN] FDIR (Queue 2) instance count is zero. Skipping parsing.")
        return []

    segments = []

    # bytes per instance = 2 * MAX_AH_INST_ID → hex chars:
    segment_len = 4 * MAX_AH_INST_ID   # hex chars

    # Payload starts at byte offset 30 → hex offset 60
    data_payload = hex_str[60:60 + count * segment_len]

    for idx in range(count):
        seg = data_payload[idx * segment_len:(idx + 1) * segment_len]
        if len(seg) < segment_len:
            continue

        sensors = []
        offset = 0

        # One s_fdir_sns_rst_err_info contains MAX_AH_INST_ID s_hw_trck_t entries
        for inst_id in range(MAX_AH_INST_ID):
            # uint8_t sns_hw_rst_cnt
            sns_hw_rst_cnt = int(seg[offset:offset + 2], 16)
            offset += 2

            # uint8_t sns_hw_err_cnt
            sns_hw_err_cnt = int(seg[offset:offset + 2], 16)
            offset += 2

            sensors.append({
                "Sensor_Inst_ID": inst_id,
                "Sensor_Inst_Str": SNS_ERR_ID_ENUM.get(inst_id, "UNKNOWN"),
                "sns_hw_rst_cnt": sns_hw_rst_cnt,
                "sns_hw_err_cnt": sns_hw_err_cnt,
            })

        segments.append({
            "Submodule_ID":        submodule_id,
            "Queue_ID":            queue_id,
            "Number of Instances": count,
            "Instance_Index":      idx,
            "Sensors_HW_Track":    sensors,
        })

    return segments
