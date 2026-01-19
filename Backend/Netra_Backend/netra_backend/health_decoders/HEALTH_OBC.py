import struct
from datetime import datetime, timezone

# -----------------------------
# MAPPINGS
# -----------------------------
FSM_STATE_MAP = {
    0: "obc init state",
    1: "obc active power critical state",
    2: "obc active power safe state",
    3: "obc active power normal state",
    4: "obc power save state",
    5: "obc reset state",
    6: "obc error state",
}

RESET_CAUSE_MAP = {
    0: "Unknown reset",
    1: "Low power reset",
    2: "Window watchdog reset",
    3: "Independent watchdog reset",
    4: "Software reset",
    5: "Power ON power down reset",
    6: "External reset pin reset",
    7: "Brownout reset",
}

MAX_TASKS = 61

# -----------------------------
# DECODER: HEALTH_OBC
# -----------------------------
def HEALTH_OBC(hex_str: str):
    # 1. Skip common metadata header (26 bytes)
    header_skip_bytes = 26
    header_skip_chars = header_skip_bytes * 2
    
    if len(hex_str) < (header_skip_chars + 8):
        print(f"[ERROR] Insufficient data length: {len(hex_str)}")
        return []

    # 2. Decoding QM metadata
    # Submodule ID: byte 26
    submodule_id = int(hex_str[header_skip_chars : header_skip_chars+2], 16)
    
    # Queue ID: byte 27
    queue_id = int(hex_str[header_skip_chars+2 : header_skip_chars+4], 16)
    
    # Number of instances: 2 bytes (UINT16) at bytes 28-29
    count_hex = hex_str[header_skip_chars+4 : header_skip_chars+8]
    count = struct.unpack('<H', bytes.fromhex(count_hex))[0]
    
    if count == 0:
        return []

    # 3. Data payload starts at byte 30
    data_start_idx = header_skip_chars + 8
    data_payload = hex_str[data_start_idx:]
    
    pos = 0
    segments = []
    
    for idx in range(count):
        # Read fixed part (31 bytes = 62 hex chars)
        fixed_len_chars = 62
        if len(data_payload[pos:]) < fixed_len_chars:
            break
            
        fixed_data = bytes.fromhex(data_payload[pos : pos + fixed_len_chars])
        pos += fixed_len_chars
        
        # Layout: 
        # Q (8): timestamp
        # B (1): fsm_state
        # B (1): num_resets
        # H (2): io_err
        # B (1): sys_err
        # f (4): cpuUtil
        # I (4): iram
        # I (4): eram
        # I (4): uptime
        # B (1): reset_cause
        # B (1): task_count
        # Total = 31 bytes
        try:
            fields = struct.unpack('<QBBHBfIIIBB', fixed_data)
        except Exception as e:
            print(f"[ERROR] Failed unpacking fixed part of instance {idx}: {e}")
            break
            
        ts64, fsm_code, resets, io_err, sys_err, cpu_util, iram, eram, uptime, cause_code, task_count = fields
        
        # Timestamp formatting
        ts_val = ts64
        # Detection logic for seconds, milliseconds, or microseconds
        if ts_val > 4102444800: # Beyond Jan 1, 2100
            if ts_val > 4102444800000: # Likely microseconds
                ts_val //= 1000000
            else: # Likely milliseconds
                ts_val //= 1000
        
        try:
            ts_human = datetime.fromtimestamp(ts_val, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            ts_human = f"INVALID_TS({ts64})"

        seg = {
            "Submodule_ID": submodule_id,
            "Queue_ID": queue_id,
            "Number of Instances": count,
            "Epoch_Time_Human": ts_human,
            "FSM_State": FSM_STATE_MAP.get(fsm_code, f"UNKNOWN({fsm_code})"),
            "Number_of_Resets": resets,
            "IO_Errors": io_err,
            "System_Errors": sys_err,
            "CPU_Utilisation": cpu_util,
            "IRAM_Rem_Heap": iram,
            "ERAM_Rem_Heap": eram,
            "Uptime": uptime,
            "Reset_Cause": RESET_CAUSE_MAP.get(cause_code, f"UNKNOWN({cause_code})"),
            "Task_Count": task_count,
        }
        
        # 4. Read task statuses (task_count * 2 bytes = 4 hex chars each)
        for i in range(MAX_TASKS):
            col_name = f"Task_{i+1:02d}_Status"
            if i < task_count:
                if len(data_payload[pos:]) < 4:
                    seg[col_name] = "MISSING_DATA"
                    continue
                task_data = bytes.fromhex(data_payload[pos : pos + 4])
                pos += 4
                st = struct.unpack('<H', task_data)[0]
                seg[col_name] = "IPC_Fail_Count" if st == 1 else "SUCCESS" if st == 0 else f"UNKNOWN({st})"
            else:
                seg[col_name] = None
        
        # If physical tasks exceed MAX_TASKS, skip those bytes to stay aligned
        if task_count > MAX_TASKS:
            pos += (task_count - MAX_TASKS) * 4
            
        segments.append(seg)
        
    return segments

if __name__ == "__main__":
    # Example usage / test
    # hex_string = "..." 
    # print(HEALTH_OBC(hex_string))
    pass