import struct
from datetime import datetime

# ---------------- ENUM TABLES ---------------- #

# Table 106: Sensor error id and IO mapped sensor error id enumeration
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

# Table 107: IO instance id enumeration (sns_intf_id)
IO_INST_ENUM = {
    0:  "INVLD_IO_INST_ID",
    1:  "IOAL_INST_I2C1",
    2:  "IOAL_INST_I2C2",
    3:  "IOAL_INST_I2C3",
    4:  "IOAL_INST_I2C4",
    5:  "IOAL_INST_SPI1",
    6:  "IOAL_INST_SPI2",
    7:  "IOAL_INST_UART1",
    8:  "IOAL_INST_UART2",
    9:  "IOAL_INST_UART3",
    10: "IOAL_INST_UART4",
    11: "IOAL_INST_UART5",
    12: "IOAL_INST_UART6",
    13: "IOAL_INST_USB1",
    14: "IOAL_INST_CAN1",
    15: "IOAL_INST_CAN2",
    16: "IOAL_INST_CAN3",
    17: "IOAL_INST_ETHERNET1",
    18: "IOAL_INST_RTC1",
    19: "IOAL_INST_QSPI1",
    20: "IOAL_INST_FMC_NOR1",
    21: "IOAL_INST_GPIO",
    22: "IOAL_INST_CRC",
    23: "IOAL_INST_ADC1",
    24: "MAX_IO_INST_ID",
}

# Table 108: Sensor error count HW type enumeration (for err_cnt_sns_tpe index)
AHW_TYPE_ENUM = {
    0:  "INVLD_AHW_TYPE",
    1:  "IMU",
    2:  "TEMP_SENSOR",
    3:  "POWER_SENSE_MONITOR",
    4:  "GPIO_EXPANDER",
    5:  "STAR_CAMERA",
    6:  "DIGI_THERM",
    7:  "HOT_SWP_CNTLR",
    8:  "THRUSTER_SENSOR",
    9:  "VOLTAGE_SEQ_MONITOR",
    10: "DATA_ACQ_DVC",
    11: "GNSS",
    12: "EXT_FLASH_MEMORY",
    13: "UART_EXPANDER",
    14: "EPS",
    15: "ADCS",
    16: "MAX_AHW_TYPE",
}

# Table 109: Recovery action enumeration (rcvy_act)
RCVY_ACT_ENUM = {
    1: "ERR_RCV_SELF_TEST_PASS",
    2: "ERR_RCV_SELF_TEST_FAIL",
    3: "ERR_RCV_RDNT_BRD_PASS",
    4: "ERR_RCV_RDNT_BRD_FAIL",
    5: "ERR_RCV_INTF_REINIT_PASS",
    6: "ERR_RCV_INTF_REINIT_FAIL",
    7: "OBC_INTF_REINIT_FAIL",
    8: "ERR_RCV_REQ_SOFT_RST_FOR_SNS",
}

MAX_AHW_TYPE = 16  # from spec


def HEALTH_FDIR_DATA_QUEUE_1(hex_str: str):
    """
    Parse TM Get Health – FDIR_DATA_QUEUE_ID (QUEUE_ID = 1).

    Payload per instance is s_fdir_sns_hm_info (28 bytes) =
        sns_err_id (1)
        io_map_sns_err_id (1)
        total_err_cnt (2)
        total_rcvy_cnt (2)
        sns_intf_id (1)
        rcvy_act (1)
        epch_tm_in_ms (4)
        err_cnt_sns_tpe[16] (16 x uint8)

    Total = 28 bytes => 56 hex chars per instance.
    """

    header_skip_len = 29  # metadata header in bytes, same as other health queues

    # TC length (not really used except for sanity)
    tc_len = struct.unpack('<H', bytes.fromhex(hex_str[46:50]))[0]
    tm_len = tc_len * 2 - 8  # kept for consistency with your other functions

    # Submodule ID and Queue ID from standard positions
    submodule_id = int(hex_str[50:52], 16)
    queue_id     = int(hex_str[52:54], 16)

    # Number of instances (at (header_skip_len - 2) bytes)
    count_offset = (header_skip_len - 2) * 2
    count = struct.unpack('<H', bytes.fromhex(hex_str[count_offset:count_offset + 4]))[0]

    if count == 0:
        print("[WARN] FDIR (Queue 1) instance count is zero. Skipping parsing.")
        return []

    segments = []

    # Each instance of s_fdir_sns_hm_info is 28 bytes = 56 hex chars
    segment_len = 56

    # Payload starts at hex_str[60:], same pattern as your ADCS function
    data_payload = hex_str[60:60 + count * segment_len]

    for idx in range(count):
        seg = data_payload[idx * segment_len:(idx + 1) * segment_len]
        if len(seg) < segment_len:
            continue

        offset = 0

        # uint8_t sns_err_id
        sns_err_id = int(seg[offset:offset + 2], 16)
        offset += 2

        # uint8_t io_map_sns_err_id
        io_map_sns_err_id = int(seg[offset:offset + 2], 16)
        offset += 2

        # uint16_t total_err_cnt
        total_err_cnt = struct.unpack('<H', bytes.fromhex(seg[offset:offset + 4]))[0]
        offset += 4

        # uint16_t total_rcvy_cnt
        total_rcvy_cnt = struct.unpack('<H', bytes.fromhex(seg[offset:offset + 4]))[0]
        offset += 4

        # uint8_t sns_intf_id
        sns_intf_id = int(seg[offset:offset + 2], 16)
        offset += 2

        # uint8_t rcvy_act
        rcvy_act = int(seg[offset:offset + 2], 16)
        offset += 2

        # uint32_t epch_tm_in_ms
        epch_tm_in_ms = struct.unpack('<I', bytes.fromhex(seg[offset:offset + 8]))[0]
        offset += 8

        # human-readable timestamp
        epch_tm_human = datetime.utcfromtimestamp(epch_tm_in_ms / 1000.0).strftime(
            '%Y-%m-%d %H:%M:%S'
        )

        # uint8_t err_cnt_sns_tpe[MAX_AHW_TYPE]
        err_cnt_sns_tpe = []
        for hw_idx in range(MAX_AHW_TYPE):
            val = int(seg[offset:offset + 2], 16)
            offset += 2
            err_cnt_sns_tpe.append({
                "HW_Type_Index": hw_idx,
                "HW_Type_Str": AHW_TYPE_ENUM.get(hw_idx, "UNKNOWN"),
                "Error_Count": val,
            })

        segments.append({
            'Submodule_ID':           submodule_id,
            'Queue_ID':               queue_id,
            'Number of Instances':    count,

            'sns_err_id':             sns_err_id,
            'sns_err_id_str':         SNS_ERR_ID_ENUM.get(sns_err_id, "UNKNOWN"),

            'io_map_sns_err_id':      io_map_sns_err_id,
            'io_map_sns_err_id_str':  SNS_ERR_ID_ENUM.get(io_map_sns_err_id, "UNKNOWN"),

            'total_err_cnt':          total_err_cnt,
            'total_rcvy_cnt':         total_rcvy_cnt,

            'sns_intf_id':            sns_intf_id,
            'sns_intf_id_str':        IO_INST_ENUM.get(sns_intf_id, "UNKNOWN"),

            'rcvy_act':               rcvy_act,
            'rcvy_act_str':           RCVY_ACT_ENUM.get(rcvy_act, "Reserved"),

            'epch_tm_in_ms':          epch_tm_in_ms,
            'epch_tm_human':          epch_tm_human,

            # list of 16 per-HW-type error counts
            'err_cnt_sns_tpe':        err_cnt_sns_tpe,
        })

    return segments
