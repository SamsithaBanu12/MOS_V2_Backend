import requests
import json
import time
import re
# API endpoint and headers
url = "http://127.0.0.1:2900/openc3-api/api"
headers = {
    "Content-Type": "application/json",
    "Authorization": "mos@1234"
}
# Fixed command string (SEQ_NO will be extracted from here)
fixed_command_str = "DRISHTI TC_CONOPS_LUT_RUN_CTRL with CSPHEADER 0x98BA7600, SOF1 0xA5, SOF2 0xAA, TC_CTRL 0x00, TIMESTAMP 1745231140, SEQ_NO 0xAF24, SAT_ID 0, GND_ID 0, QOS 3, SA_ID 1, DA_ID 0x8180, RM_ID 4, TC_ID 0xA402, TC_LEN 2, LUT_NUM 0, ACTION 4"
# Extract SEQ_NO value using regex
match = re.search(r"SEQ_NO 0x([0-9A-Fa-f]+)", fixed_command_str)
if not match:
    print("Failed to extract SEQ_NO from the command string.")
    exit(1)
sent_seq_no_hex = match.group(1).lower()  # e.g. 'af20'
# Send the fixed command
fixed_command = {
    "jsonrpc": "2.0",
    "method": "cmd",
    "params": [fixed_command_str],
    "id": 2719,
    "keyword_params": {"scope": "DEFAULT"}
}
response = requests.post(url, headers=headers, data=json.dumps(fixed_command))
print("Fixed Command Response:", response.json())
# Wait a few seconds to allow new telemetry to be received
print("Waiting for telemetry to update...")
time.sleep(5)
# Wait for telemetry to confirm execution
while True:
    tlm_check_command = {
        "jsonrpc": "2.0",
        "method": "get_tlm_packet",
        "params": ["DRISHTI", "TM_CONOPS_SCH_LUT_RUN_CTRL"],
        "id": 2719,
        "keyword_params": {"scope": "DEFAULT"}
    }
    tlm_response = requests.post(url, headers=headers, data=json.dumps(tlm_check_command))
    tlm_data = tlm_response.json()
    result = tlm_data.get("result", [])
    coid_value = None
    for field in result:
        if field[0] == "COID":
            coid_value = field[1]  # should be int
            break
    if coid_value is not None:
        coid_hex = f"{coid_value:04x}"
        if coid_hex == sent_seq_no_hex:
            print(f"Command {sent_seq_no_hex.upper()} executed successfully.")
            break
        else:
            print(f"Command {sent_seq_no_hex.upper()} execution failed. COID = {coid_hex.upper()}")
            exit(1)
    else:
        print("Waiting for COID in telemetry...")
        time.sleep(1)
# Load commands from JSON file
with open('schedule.json', 'r') as file:
    schedule = json.load(file)
commands_per_batch = 5
address_offset = 0
for i in range(0, len(schedule), commands_per_batch):
    batch = schedule[i:i + commands_per_batch]
    payload = ""
    for command in batch:
        sequence = command.get("sequence", "")
        if sequence:
            seq_bytes = ''.join(f"{int(b,16):02x}" for b in sequence.split(","))
            payload += "04" + seq_bytes
        else:
            payload += "04"
    payload_bytes = bytes.fromhex(payload)
    total_length = len(payload_bytes)
    offset_address_length = 4  # bytes
    total_length_field_length = 2  # bytes
    total_size = total_length + offset_address_length + total_length_field_length
    total_size_hex = total_size.to_bytes(2, byteorder='little').hex()
    address_offset_hex = address_offset.to_bytes(offset_address_length, byteorder='little').hex()
    total_length_hex = total_length.to_bytes(total_length_field_length, byteorder='little').hex()
    pdu_hex = total_size_hex + address_offset_hex + total_length_hex + payload
    command_payload = {
        "jsonrpc": "2.0",
        "method": "cmd",
        "params": [
            f"DRISHTI TC_DEFFERED_STRG_OPT with CSPHEADER 0x98BA7600, SOF1 0xA5, SOF2 0xAA, TC_CTRL 0x00, TIMESTAMP 1745231140, SEQ_NO 0xAE15, SAT_ID 0, GND_ID 0, QOS 3, SA_ID 1, DA_ID 0x8180, RM_ID 4, TC_ID 0xB502, PDU 0x{pdu_hex}"
        ],
        "id": 2719,
        "keyword_params": {"scope": "DEFAULT"}
    }
    response = requests.post(url, headers=headers, data=json.dumps(command_payload))
    print(f"Batch {i // commands_per_batch + 1} Response:", response.json())
    address_offset += total_length
    

with open("schedule.json", "r") as f:
    schedule = json.load(f)

# OpenC3 API details
url = "http://127.0.0.1:2900/openc3-api/api"
headers = {
    "Content-Type": "application/json",
    "Authorization":"mos@1234"
}

# Max events per 547 command
events_per_segment = 11
segments = [schedule[i:i + events_per_segment] for i in range(0, len(schedule), events_per_segment)]
total_segments = len(segments)

# Compute payload length and address for each event in sequence
payload_info = []
address = 0

for command in schedule:
    sequence = command.get("sequence", "")
    if sequence:
        bytes_list = sequence.split(",")
        length = len(bytes_list)  # ✅ Each entry is 1 byte
    else:
        length = 0

    payload_info.append({
        "epoch": int(command.get("epoch", 0)),
        "ms": 0x01,
        "src": 0x01,
        "dest": int(command.get("dest_id", 1)) & 0xFF,
        "tc_id": 0xA302,
        "addr": address,
        "length": length
    })

    address = address + length + 1

# Define hardcoded hex values per event (optional override)
# Each list item should be a full 34-char hex string for one event (or empty string to use dynamic encoding)
# Dynamically build manual_event_hex from schedule.json
manual_event_hex = []

# Set first epoch manually
first_epoch = 1751089850  # change as needed

# Compute timestamps for all entries
timestamp_list = [first_epoch]
for i in range(1, len(schedule)):
    prev_time = timestamp_list[-1]
    interval = int(schedule[i].get("interval", 0))
    timestamp_list.append(prev_time + interval)

# Build hex strings with computed timestamps
for idx, entry in enumerate(schedule):
    epoch = timestamp_list[idx]
    epoch_hex = epoch.to_bytes(4, byteorder='little').hex()

    ms = entry.get("ms", "00")
    src = entry.get("SrcID", "00")
    dest = entry.get("DestID", "00")
    tcid = entry.get("TCID", "0000")
    addr = entry.get("Length", "00000000")
    length = entry.get("Address", "00000000")

    hex_string = epoch_hex + ms + src + dest + tcid + addr + length
    manual_event_hex.append(hex_string)


start_idx = 0
for segment_id, segment in enumerate(segments):
    event_block = ""

    # Header: 5 bytes
    lookup_table_id = 0x00
    reserved = 0x00
    num_events = len(segment)
    event_block += f"{lookup_table_id:02x}{total_segments:02x}{segment_id:02x}{reserved:02x}{num_events:02x}"

    # Add event data
    for i in range(num_events):
        index = start_idx + i
        if index < len(manual_event_hex) and manual_event_hex[index]:
            # Use manually hardcoded hex string
            event_block += manual_event_hex[index]
        else:
            # Fallback to dynamic encoding
            info = payload_info[index]
            epoch_hex = info["epoch"].to_bytes(4, byteorder='little').hex()
            ms_hex = f"{info['ms']:02x}"
            src_hex = f"{info['src']:02x}"
            dest_hex = f"{info['dest']:02x}"
            tc_id_hex = f"{info['tc_id']:04x}"
            addr_hex = info["addr"].to_bytes(4, byteorder='little').hex()
            length_hex = info["length"].to_bytes(4, byteorder='little').hex()

            event_block += (
                epoch_hex +
                ms_hex +
                src_hex +
                dest_hex +
                tc_id_hex +
                addr_hex +
                length_hex
            )

    # Calculate TC_LEN dynamically from event block size (in bytes)
    tc_len_bytes = len(event_block) // 2
    tc_len_decimal = tc_len_bytes

    # Build final command string
    event_command_str = (
        f"DRISHTI TC_547 with CSPHEADER 0x98BA7600, SOF1 0xA5, SOF2 0xAA, "
        f"TC_CTRL 0x00, TIMESTAMP 1745231140, SEQ_NO 0xAE14, SAT_ID 0, GND_ID 0, QOS 3, "
        f"SA_ID 1, DA_ID 0x8180, RM_ID 4, TC_ID 0xA302, TC_LEN {tc_len_decimal}, EVENT 0x{event_block}"
    )

    command_payload = {
        "jsonrpc": "2.0",
        "method": "cmd",
        "params": [event_command_str],
        "id": 2719,
        "keyword_params": {"scope": "DEFAULT"}
    }

    print(f"\n🚀 Sending 547 Command Segment {segment_id + 1}/{total_segments}")
    response = requests.post(url, headers=headers, data=json.dumps(command_payload))
    try:
        print("Response:", response.json())
    except Exception:
        print("Response error:", response.status_code, response.text)

    start_idx += num_events
    time.sleep(2)