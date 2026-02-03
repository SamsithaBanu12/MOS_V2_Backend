#!/usr/bin/env python3
import os
import sys
import time
import threading
import asyncio
from typing import Set, Optional, List, Dict
from collections import deque
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
import uvicorn

# ---------- OPEN C3 CONNECTION CONFIG ----------
os.environ["OPENC3_SCOPE"] = os.getenv("OPENC3_SCOPE", "DEFAULT")
os.environ["OPENC3_API_HOSTNAME"] = os.getenv("OPENC3_API_HOSTNAME", "127.0.0.1")
os.environ["OPENC3_API_PORT"] = os.getenv("OPENC3_API_PORT", "2900")
os.environ["OPENC3_API_PASSWORD"] = os.getenv("OPENC3_API_PASSWORD", "mos12345")

from openc3.script.web_socket_api import StreamingWebSocketApi

# ---------------------------------------------------------
# 1️⃣  TELEMETRY PACKETS (TLM)
# ---------------------------------------------------------
PACKETS_TLM = [
    "RAW__TLM__EMULATOR__HEALTH_ADCS_CMD_ATTITUDE_ANGLE",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_CONS_CURRENT",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_CSS_VECTOR",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_CURRENT_STATE",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_EST_ATTITUDE_ANGLE",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_EST_GYRO_BIAS",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_EST_INNOV",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_EST_RATES",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_FINE_EST_ANG_RATES",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_FSS_VECTOR",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_IGRF_MOD_VEC",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_MAG_FIELD_VEC",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_MEAS_RW_SPEED",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_MGTRQR_CMD",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_MISC_CURRENT",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_NADAR_VEC",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_POS_LLH",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_QUAT_ERR_VEC",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_RATE_SENSOR_MEASURE",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_RATE_SENSOR_TEMP",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_RAW_CSS",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_RAW_FSS_SNS",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_RAW_MAG_MEASURE",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_RAW_NADAR_SNS",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_RAW_RATE_SENSOR_MEASURE",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_RAW_STAR_TRKR_MEAS",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_RW_CURRENT",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_RW_SPEED_CMD",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_SAT_POS_ECEF_FRAME",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_SAT_POS_ECI_FRAME",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_SAT_VEL_ECI_FRAME",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_SENSOR_CURRENT",
    "RAW__TLM__EMULATOR__HEALTH_ADCS_TEMP",
    "RAW__TLM__EMULATOR__HEALTH_COMS_S",
    "RAW__TLM__EMULATOR__HEALTH_COMS_UHF",
    "RAW__TLM__EMULATOR__HEALTH_EPS",
    "RAW__TLM__EMULATOR__HEALTH_ERROR_HANDLER",
    "RAW__TLM__EMULATOR__HEALTH_II_411_BEACON_DATA",
    "RAW__TLM__EMULATOR__HEALTH_II_ADCS_POS_LLH",
    "RAW__TLM__EMULATOR__HEALTH_II_ADCS_SAT_POS_ECEF_FRAME",
    "RAW__TLM__EMULATOR__HEALTH_II_ADCS_SAT_POS_ECI_FRAME",
    "RAW__TLM__EMULATOR__HEALTH_II_EPS",
    "RAW__TLM__EMULATOR__HEALTH_OBC",
    "RAW__TLM__EMULATOR__HEALTH_SENSORS_DT_EDGE_DATA",
    "RAW__TLM__EMULATOR__HEALTH_SENSORS_DT_PS_DATA",
    "RAW__TLM__EMULATOR__HEALTH_SENSORS_HSC_EDGE_DATA",
    "RAW__TLM__EMULATOR__HEALTH_SENSORS_HSC_PS1_DATA",
    "RAW__TLM__EMULATOR__HEALTH_SENSORS_HSC_PS2_DATA",
    "RAW__TLM__EMULATOR__HEALTH_SENSORS_PSM_OBC_DATA",
    "RAW__TLM__EMULATOR__HEALTH_SENSORS_PSM_PS_DATA",
    "RAW__TLM__EMULATOR__HEALTH_SENSORS_TEMP_ES_DATA",
    "RAW__TLM__EMULATOR__HEALTH_SENSORS_TEMP_GPS_DATA",
    "RAW__TLM__EMULATOR__HEALTH_SENSORS_TEMP_OBC_DATA",
    "RAW__TLM__EMULATOR__HEALTH_SENSORS_TEMP_PS_DATA",
    "RAW__TLM__EMULATOR__HEALTH_SENSORS_TEMP_SPB01_DATA",
    "RAW__TLM__EMULATOR__HEALTH_SENSORS_TEMP_SPE01_DATA",
    "RAW__TLM__EMULATOR__HEALTH_SENSORS_TEMP_SPE02_DATA",
    "RAW__TLM__EMULATOR__HEALTH_SENSORS_TEMP_SPW01_DATA",
    "RAW__TLM__EMULATOR__HEALTH_SENSORS_TEMP_SPW02_DATA",
    "DECOM__TLM__EMULATOR__THRUSTER_1021_TM_EXOTRAIL_GET_SYS_INFO",
    "DECOM__TLM__EMULATOR__THRUSTER_1022_TM_EXOTRAIL_GET_HEAT_ACTIVITY",
    "DECOM__TLM__EMULATOR__THRUSTER_1023_TM_EXOTRAIL_GET_HK_FLUIDIC_INFO",
    "DECOM__TLM__EMULATOR__THRUSTER_1024_TM_EXOTRAIL_GET_HK_FLUIDIC_INFO",
    "DECOM__TLM__EMULATOR__THRUSTER_1025_TM_EXOTRAIL_GET_HK_THERMIC_INFO",
    "DECOM__TLM__EMULATOR__OBC_581_TM_GET_CUR_TIME",
    "DECOM__TLM__EMULATOR__THRUSTER_1026_TM_EXOTRAIL_GET_HK_POWER_INFO",
    "DECOM__TLM__EMULATOR__THRUSTER_1027_TM_EXOTRAIL_GET_HK_FLUIDIC_INFO",
    "DECOM__TLM__EMULATOR__THRUSTER_1028_TM_EXOTRAIL_GET_FLUIDIC_VALVE_SEL",
    "DECOM__TLM__EMULATOR__THRUSTER_1029_TM_EXOTRAIL_GET_HEATER_CFG",
    "DECOM__TLM__EMULATOR__THRUSTER_1030_TM_EXOTRAIL_SET_FIRING_OPERATING_POINT",
    "DECOM__TLM__EMULATOR__THRUSTER_1031_TM_EXOTRAIL_TEST_SET_OBC_MODE",
    "DECOM__TLM__EMULATOR__THRUSTER_1033_TM_EXOTRAIL_SET_SAFE_LIMIT",
    "DECOM__TLM__EMULATOR__THRUSTER_1034_TM_EXOTRAIL_SET_FLUIDIC_VALVE_SEL",
    "DECOM__TLM__EMULATOR__THRUSTER_1036_TM_EXOTRAIL_SET_FIRING_DURATION",
    "DECOM__TLM__EMULATOR__THRUSTER_1038_TM_OBC_EXOTRIAL_THRUSTER_TM_DECODE_DATA",
    "DECOM__TLM__EMULATOR__OBC_500_TM_GET_PROC_UTIL_INFO",
    "DECOM__TLM__EMULATOR__OBC_550_TM_SET_CUR_TIME",
    "DECOM__TLM__EMULATOR__TM_547",
    "DECOM__TLM__EMULATOR__549_TM",
    "DECOM__TLM__EMULATOR__TM_CONOPS_SCH_LUT_RUN_CTRL",
    "DECOM__TLM__EMULATOR__TM_DEFERRED_STORAGE",
    "DECOM__TLM__EMULATOR__4999_ERROR",
    "DECOM__TLM__EMULATOR__117_TTY_DEBUG",
    "DECOM__TLM__EMULATOR__615_START_FTM",
    "DECOM__TLM__EMULATOR__616_STOP_FTM",
    "DECOM__TLM__EMULATOR__COMMS_350_TM_GET_SBAND_TX_CFG",
    "DECOM__TLM__EMULATOR__COMMS_369_TM_GET_SBAND_RX_CFG",
    "DECOM__TLM__EMULATOR__COMMS_420_TM_SBAND_GET_RX_SEL_CFG",
    "DECOM__TLM__EMULATOR__COMMS_465_TM_SBAND_GET_COMMS_TM_INFO",
    "DECOM__TLM__EMULATOR__COMMS_468_TM_SBAND_GET_PROD_KEY",

    "DECOM__TLM__EMULATOR__ADCS_19_TM_SET_ADCS_CTRL_MODE_CONF",
    "DECOM__TLM__EMULATOR__ADCS_129_TM_GET_ADCS_STATE_INFO",
    "DECOM__TLM__EMULATOR__ADCS_137_TM_GET_ADCS_MEAS_RATE",
    "DECOM__TLM__EMULATOR__ADCS_184_TM_GET_ADCS_EST_RATE",
    "DECOM__TLM__EMULATOR__ADCS_241_TM_GET_ADCS_EST_ATTITUDE",
    "DECOM__TLM__EMULATOR__ADCS_177_TC_GET_ADCS_CMD_ATTITUDE",
    "DECOM__TLM__EMULATOR__ADCS_253_TM_ADCS_STATE_CFG",
    "DECOM__TLM__EMULATOR__ADCS_195_TM_GET_ADCS_RW_SPEED_DATA",
    "DECOM__TLM__EMULATOR__ADCS_196_TM_GET_ADCS_RW_SPEED_MEASURE",
    "DECOM__TLM__EMULATOR__ADCS_142_TC_GET_ADCS_RW_MAGMTR",
    "DECOM__TLM__EMULATOR__ADCS_248_TM_GET_ADCS_RAW_CSS",
    "DECOM__TLM__EMULATOR__ADCS_187_TM_GET_ADCS_MODL_MAG_VEC_DATA",
    "DECOM__TLM__EMULATOR__ADCS_188_TM_GET_ADCS_MODL_SUN_VEC_DATA",
    "DECOM__TLM__EMULATOR__ADCS_181_TM_GET_ADCS_SAT_POS_ECI",
    "DECOM__TLM__EMULATOR__ADCS_182_TM_GET_ADCS_SAT_VELOCITY_DATA",
    "DECOM__TLM__EMULATOR__ADCS_111_TM_GET_ADCS_ERR_VALID_METRICS",
    "DECOM__TLM__EMULATOR__ADCS_133_TM_GET_ADCS_MAG_FIELD_VEC",
    "DECOM__TLM__EMULATOR__ADCS_117_TM_GET_ADCS_SAT_VEL_ECEF",
    "DECOM__TLM__EMULATOR__ADCS_134_TM_GET_ADCS_CSS_VEC",

    "DECOM__TLM__EMULATOR__OBC_610_TM_GET_TEMP",
    "DECOM__TLM__EMULATOR__OBC_611_TM_GET_TIME",
    "DECOM__TLM__EMULATOR__OBC_545_TM_PLD_VM_PWR_ON",
    "DECOM__TLM__EMULATOR__OBC_546_TM_PLD_VM_PWR_OFF",
    "DECOM__TLM__EMULATOR__OBC_508_TM_CONFIG_AUTO_LEOP_TRIGGER_TMR",
    "DECOM__TLM__EMULATOR__OBC_508_TM_TRIGGER_HINGE_PROCESS",
    "DECOM__TLM__EMULATOR__OBC_505_TM_GET_AUTO_LEOPS_STATE",
    "DECOM__TLM__EMULATOR__OBC_602_TM_TRIGGER_HINGE_PROCESS",
    "DECOM__TLM__EMULATOR__COMMS_350_TM_GET_SBAND_TX_CFG",
    "DECOM__TLM__EMULATOR__COMMS_369_TM_GET_SBAND_RX_CFG",
    "DECOM__TLM__EMULATOR__COMMS_420_TM_SBAND_GET_RX_SEL_CFG",
    "DECOM__TLM__EMULATOR__COMMS_465_TM_SBAND_GET_COMMS_TM_INFO",
    "DECOM__TLM__EMULATOR__COMMS_468_TM_SBAND_GET_PROD_KEY",
    "DECOM__TLM__EMULATOR__200_EPS_TM_GET_SUB_SYS_INFO",
    "DECOM__TLM__EMULATOR__216_EPS_TM_SET_EPS_CTRL_DEV_TMR",
    "DECOM__TLM__EMULATOR__217_EPS_TM_GET_EPS_CTRL_DEV_TMR",
    "DECOM__TLM__EMULATOR__211_EPS_TM_SET_DEVICE_STS",
    "DECOM__TLM__EMULATOR__212_EPS_TM_GET_DEVICE_STS",
    "DECOM__TLM__EMULATOR__OBC_256_TM_GET_OBC_NVM_REVISION_NUM",
    "DECOM__TLM__EMULATOR__ADCS_142_TM_GET_ADCS_RW_MAGMTR",
    "DECOM__TLM__EMULATOR__OBC_638_TM_GET_MCU_RST_INFO",
    "DECOM__TLM__EMULATOR__OBC_598_TM_CONFIG_OBC_SELF_RST_TMR",
    "DECOM__TLM__EMULATOR__OBC_599_TM_PS_ES_CONFIG_KEEP_ALIVE_RCVRY_TMOUT",
]
# ---------------------------------------------------------
# :two:  COMMAND PACKETS (CMD)
# ---------------------------------------------------------
PACKETS_CMD = [
    "DECOM__CMD__EMULATOR__FTM_SEND_DATA_PCKTS",
    "DECOM__CMD__EMULATOR__OBC_500_TC_GET_PROC_UTIL_INFO",
    "DECOM__CMD__EMULATOR__OBC_550_TC_SET_CUR_TIME",
    "DECOM__CMD__EMULATOR__OBC_581_TC_GET_CUR_TIME",
    "DECOM__CMD__EMULATOR__TC_547",
    "DECOM__CMD__EMULATOR__TC_549",
    "DECOM__CMD__EMULATOR__TC_CONOPS_LUT_RUN_CTRL",
    "DECOM__CMD__EMULATOR__TC_DEFFERED_STRG_OPT",
    "DECOM__CMD__EMULATOR__THRUSTER_1021_TC_EXOTRAIL_GET_SYS_INFO",
    "DECOM__CMD__EMULATOR__THRUSTER_1022_TC_EXOTRAIL_GET_HEAT_ACTIVITY",
    "DECOM__CMD__EMULATOR__THRUSTER_1023_TC_EXOTRAIL_GET_HK_FLUIDIC_INFO",
    "DECOM__CMD__EMULATOR__THRUSTER_1024_TC_EXOTRAIL_GET_HK_FLUIDIC_INFO",
    "DECOM__CMD__EMULATOR__THRUSTER_1025_TC_EXOTRAIL_GET_HK_THERMIC_INFO",
    "DECOM__CMD__EMULATOR__THRUSTER_1026_TC_EXOTRAIL_GET_HK_POWER_INFO",
    "DECOM__CMD__EMULATOR__THRUSTER_1027_TC_EXOTRAIL_GET_SAFE_LIMIT",
    "DECOM__CMD__EMULATOR__THRUSTER_1028_TC_EXOTRAIL_GET_FLUIDIC_VALVE_SEL",
    "DECOM__CMD__EMULATOR__THRUSTER_1029_TC_EXOTRAIL_GET_HEATER_CFG",
    "DECOM__CMD__EMULATOR__THRUSTER_1030_TC_EXOTRAIL_SET_FIRING_OPERATING_POINT",
    "DECOM__CMD__EMULATOR__THRUSTER_1031_TC_EXOTRAIL_TEST_SET_OBC_MODE",
    "DECOM__CMD__EMULATOR__THRUSTER_1033_TC_EXOTRAIL_SET_SAFE_LIMIT",
    "DECOM__CMD__EMULATOR__THRUSTER_1034_TC_EXOTRAIL_SET_FLUIDIC_VALVE_SEL",
    "DECOM__CMD__EMULATOR__THRUSTER_1036_TC_EXOTRAIL_SET_FIRING_DURATION",
    "DECOM__CMD__EMULATOR__THRUSTER_1038_TC_OBC_EXOTRIAL_THRUSTER_TM_DECODE_DATA",
    "DECOM__CMD__EMULATOR__117_TTY_DEBUG",
    "DECOM__CMD__EMULATOR__200_EPS_TC_GET_SUB_SYS_INFO",
    "DECOM__CMD__EMULATOR__615_START_FTM",
    "DECOM__CMD__EMULATOR__616_STOP_FTM",
    "DECOM__CMD__EMULATOR__COMMS_350_TC_GET_SBAND_TX_CFG",
    "DECOM__CMD__EMULATOR__COMMS_369_TC_GET_SBAND_RX_CFG",
    "DECOM__CMD__EMULATOR__COMMS_420_TC_SBAND_GET_RX_SEL_CFG",
    "DECOM__CMD__EMULATOR__COMMS_463_TC_SBAND_GET_DEVICE_CONF",
    "DECOM__CMD__EMULATOR__COMMS_465_TC_SBAND_GET_COMMS_TM_INFO",
    "DECOM__CMD__EMULATOR__COMMS_468_TC_SBAND_GET_PROD_KEY",

    "DECOM__CMD__EMULATOR__ADCS_19_TC_3_AXIS_STABALISATION_MODE",
    "DECOM__CMD__EMULATOR__ADCS_19_TC_SUN_POINTING_CONTROL_MODE",
    "DECOM__CMD__EMULATOR__ADCS_19_TC_NADIR_POINTING",
    "DECOM__CMD__EMULATOR__ADCS_19_TC_TARGET_TRACKING_CONTROL_MODE_ECEF_TARGET_REFERENCE",
    "DECOM__CMD__EMULATOR__ADCS_19_TC_TARGET_TRACKING_CONTROL_MODE_WITH_ADDITIONAL_CONTROL",
    "DECOM__CMD__EMULATOR__ADCS_19_TC_FINE_SUN_POINTING",
    "DECOM__CMD__EMULATOR__ADCS_129_TC_GET_ADCS_STATE_INFO",
    "DECOM__CMD__EMULATOR__ADCS_137_TC_GET_ADCS_MEAS_RATE",
    "DECOM__CMD__EMULATOR__ADCS_184_TC_GET_ADCS_EST_RATE",
    "DECOM__CMD__EMULATOR__ADCS_241_TC_GET_ADCS_EST_ATTITUDE",
    "DECOM__CMD__EMULATOR__ADCS_177_TC_GET_ADCS_CMD_ATTITUDE",
    "DECOM__CMD__EMULATOR__ADCS_253_TC_ADCS_STATE_CFG",   
    "DECOM__CMD__EMULATOR__ADCS_195_TC_GET_ADCS_RW_SPEED_DATA",
    "DECOM__CMD__EMULATOR__ADCS_196_TC_GET_ADCS_RW_SPEED_MEASURE",
    "DECOM__CMD__EMULATOR__ADCS_142_TC_GET_ADCS_RW_MAGMTR",
    "DECOM__CMD__EMULATOR__ADCS_248_TC_GET_ADCS_RAW_CSS",
    "DECOM__CMD__EMULATOR__ADCS_187_TC_GET_ADCS_MODL_MAG_VEC_DATA",
    "DECOM__CMD__EMULATOR__ADCS_188_TC_GET_ADCS_MODL_SUN_VEC_DATA",
    "DECOM__CMD__EMULATOR__ADCS_181_TC_GET_ADCS_SAT_POS_ECI",
    "DECOM__CMD__EMULATOR__ADCS_182_TC_GET_ADCS_SAT_VELOCITY_DATA",
    "DECOM__CMD__EMULATOR__ADCS_111_TC_GET_ADCS_ERR_VALID_METRICS",
    "DECOM__CMD__EMULATOR__ADCS_133_TC_GET_ADCS_MAG_FIELD_VEC",
    "DECOM__CMD__EMULATOR__ADCS_117_TC_GET_ADCS_SAT_VEL_ECEF",
    "DECOM__CMD__EMULATOR__ADCS_134_TC_GET_ADCS_CSS_VEC",

    "DECOM__CMD__EMULATOR__OBC_610_TC_GET_TEMP",
    "DECOM__CMD__EMULATOR__OBC_611_TC_GET_TIME",
    "DECOM__CMD__EMULATOR__OBC_621_OPTION_1_TC_GET_HEALTH_METRICS",
    "DECOM__CMD__EMULATOR__OBC_621_OPTION_2_TC_GET_HEALTH_METRICS",
    "DECOM__CMD__EMULATOR__OBC_621_OPTION_3_TC_GET_HEALTH_METRICS",
    "DECOM__CMD__EMULATOR__OBC_1042_TC_EXOTRAIL_GET_PRPLT_TANK_TEMP",
    "DECOM__CMD__EMULATOR__OBC_545_TC_PLD_VM_PWR_ON",
    "DECOM__CMD__EMULATOR__OBC_546_TC_PLD_VM_PWR_OFF",
    "DECOM__CMD__EMULATOR__OBC_508_TC_CONFIG_AUTO_LEOP_TRIGGER_TMR",
    "DECOM__CMD__EMULATOR__OBC_508_TC_TRIGGER_HINGE_PROCESS",
    "DECOM__CMD__EMULATOR__OBC_505_TC_GET_AUTO_LEOPS_STATE",
    "DECOM__CMD__EMULATOR__OBC_602_TC_TRIGGER_HINGE_PROCESS",
    "DECOM__CMD__EMULATOR__COMMS_350_TC_GET_SBAND_TX_CFG",
    "DECOM__CMD__EMULATOR__COMMS_369_TC_GET_SBAND_RX_CFG",
    "DECOM__CMD__EMULATOR__COMMS_420_TC_SBAND_GET_RX_SEL_CFG",
    "DECOM__CMD__EMULATOR__COMMS_463_TC_SBAND_GET_DEVICE_CONF",
    "DECOM__CMD__EMULATOR__COMMS_465_TC_SBAND_GET_COMMS_TM_INFO",
    "DECOM__CMD__EMULATOR__COMMS_468_TC_SBAND_GET_PROD_KEY",
    "DECOM__CMD__EMULATOR__200_EPS_TC_GET_SUB_SYS_INFO",
    "DECOM__CMD__EMULATOR__216_EPS_TC_SET_EPS_CTRL_DEV_TMR",
    "DECOM__CMD__EMULATOR__217_EPS_TC_GET_EPS_CTRL_DEV_TMR",
    "DECOM__CMD__EMULATOR__211_EPS_TC_SET_DEVICE_STS",
    "DECOM__CMD__EMULATOR__202_TC_SET_EPS_CONF_OPTION_1",
    "DECOM__CMD__EMULATOR__212_EPS_TC_GET_DEVICE_STS",
    "DECOM__CMD__EMULATOR__OBC_256_TC_GET_OBC_NVM_REVISION_NUM",
    "DECOM__CMD__EMULATOR__ADCS_142_TC_GET_ADCS_RW_MAGMTR",
    "DECOM__CMD__EMULATOR__OBC_638_TC_GET_MCU_RST_INFO",
    "DECOM__CMD__EMULATOR__OBC_621_TC_GET_HEALTH_METRICS_PRIORITY_BASED_QUEUES_IN_ALL_SUBMODULES",
    "DECOM__CMD__EMULATOR__OBC_621_TC_GET_HEALTH_METRICS_ONE_SUBMODULE_ONE_QUEUE",
    "DECOM__CMD__EMULATOR__OBC_621_TC_GET_HEALTH_METRICS_ONE_SUBMODULE_MULTIPLE_QUEUES",
    "DECOM__CMD__EMULATOR__OBC_598_TC_CONFIG_OBC_SELF_RST_TMR",
    "DECOM__CMD__EMULATOR__OBC_599_TC_PS_ES_CONFIG_KEEP_ALIVE_RCVRY_TMOUT",
]

# 3️⃣  OPTIONAL ITEM STREAMING (leave empty)
# ---------------------------------------------------------
ITEMS_TO_STREAM: List[str] = []

# ---------------------------------------------------------
# 4️⃣  FASTAPI APP + STATE
# ---------------------------------------------------------
app = FastAPI(
    title="OpenC3 Telemetry Stream",
    description="Streams OpenC3 telemetry/command packets via WebSocket and REST endpoints.",
    version="1.0.0",
)
ALLOWED_CORS = ["http://localhost:8012", "http://127.0.0.1:8012", "*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_CORS, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Connected WebSocket clients
connected_clients: Set[WebSocket] = set()

# Main event loop (for sending from background thread)
main_event_loop: Optional[asyncio.AbstractEventLoop] = None

# In-memory buffer of recent packets (for REST)
PACKET_BUFFER_SIZE = 1000
packet_buffer: deque[Dict] = deque(maxlen=PACKET_BUFFER_SIZE)
packet_buffer_lock = threading.Lock()


def openc3_streamer(loop: asyncio.AbstractEventLoop):
    """
    Runs in a background thread:
    - Connect to OpenC3 via StreamingWebSocketApi
    - Read packets forever
    - Save packets in buffer
    - Broadcast each packet as JSON to all connected WebSockets
    """
    packets_to_stream = PACKETS_TLM + PACKETS_CMD

    if not packets_to_stream and not ITEMS_TO_STREAM:
        raise RuntimeError("Nothing configured to stream")

    with StreamingWebSocketApi() as api:
        if packets_to_stream:
            api.add(packets=packets_to_stream, start_time=None, end_time=None)
        elif ITEMS_TO_STREAM:
            api.add(items=ITEMS_TO_STREAM, start_time=None, end_time=None)

        print("✅ Connected to OpenC3 – streaming to FastAPI clients...", file=sys.stderr)

        while True:
            try:
                batch = api.read()
            except Exception as e:
                print(f"❌ Error reading from OpenC3: {e}", file=sys.stderr)
                time.sleep(1.0)
                continue

            if not batch:
                time.sleep(0.05)
                continue

            for pkt in batch:
                pkt_name = pkt.get("__packet", "<no __packet field>")
                print(f"📥 Received packet: {pkt_name}", file=sys.stderr)

                # 1) Store in in-memory buffer
                with packet_buffer_lock:
                    packet_buffer.append(pkt)

                # 2) Broadcast to WebSocket clients
                for ws in list(connected_clients):
                    try:
                        asyncio.run_coroutine_threadsafe(ws.send_json(pkt), loop)
                    except Exception as e:
                        print(f"⚠️ Error sending to client: {e}", file=sys.stderr)


@app.on_event("startup")
async def startup_event():
    """Start the background OpenC3 streaming thread on app startup."""
    global main_event_loop
    main_event_loop = asyncio.get_event_loop()

    t = threading.Thread(
        target=openc3_streamer,
        args=(main_event_loop,),
        daemon=True,
    )
    t.start()
    print("🚀 Background OpenC3 streaming thread started", file=sys.stderr)


# ---------------------------------------------------------
# 5️⃣  WEBSOCKET ENDPOINT
# ---------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    WebSocket endpoint for frontend clients.
    Each connected client will receive every packet as a JSON message.
    """
    await ws.accept()
    connected_clients.add(ws)
    print("👤 Client connected", file=sys.stderr)

    try:
        # Keep the connection alive; we don't really care about incoming messages.
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        print("👤 Client disconnected", file=sys.stderr)
    finally:
        connected_clients.discard(ws)


# ---------------------------------------------------------
# 6️⃣  REST ENDPOINTS (visible & testable in /docs)
# ---------------------------------------------------------
@app.get("/packets", summary="Get recent packets")
def get_packets(limit: int = 2000) -> List[Dict]:
    """
    Return the most recent packets (up to 'limit').
    Use this from Swagger UI at /docs to quickly inspect data.
    """
    if limit <= 0:
        limit = 1
    if limit > PACKET_BUFFER_SIZE:
        limit = PACKET_BUFFER_SIZE

    with packet_buffer_lock:
        data = list(packet_buffer)

    # Take the last N packets; returned oldest -> newest within that slice
    return data[-limit:]


@app.get("/latest", summary="Get the latest packet")
def get_latest_packet() -> Dict:
    """
    Return the most recently received packet.
    """
    with packet_buffer_lock:
        if not packet_buffer:
            raise HTTPException(status_code=404, detail="No packets received yet")
        latest = packet_buffer[-1]
    return latest


# ---------------------------------------------------------
# 7️⃣  ENTRY POINT – run FastAPI on port 8012
# ---------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8012, reload=False)