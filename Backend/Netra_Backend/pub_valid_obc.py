import paho.mqtt.client as mqtt
import struct
import time

BROKER_HOST = "127.0.0.1"
BROKER_PORT = 2147
TOPIC = "cosmos/telemetry"

def create_valid_packet():
    # 1. Header: 26 bytes of dummy data (zeros or pattern)
    header = b'\x00' * 26
    
    # 2. Submodule ID (u8) = 5
    submodule = struct.pack("B", 5)
    
    # 3. Queue ID (u8) = 0
    queue = struct.pack("B", 0)
    
    # 4. Instance Count (u16le) = 1
    inst_count = struct.pack("<H", 1)
    
    # -- Instance 0 Data --
    # Timestamp (u64le) = current unix timestamp
    ts = struct.pack("<Q", int(time.time()))
    
    # FSM State (u8) = 3 (normal)
    fsm = struct.pack("B", 3)
    
    # Resets (u8) = 0
    resets = struct.pack("B", 0)
    
    # IO Errors (u16le) = 0
    io_err = struct.pack("<H", 0)
    
    # Sys Errors (u8) = 0
    sys_err = struct.pack("B", 0)
    
    # CPU Util (f32le) = 12.5
    cpu = struct.pack("<f", 12.5)
    
    # IRAM (u32le) = 1000
    iram = struct.pack("<I", 1000)
    
    # ERAM (u32le) = 2000
    eram = struct.pack("<I", 2000)
    
    # Uptime (u32le) = 3600
    uptime = struct.pack("<I", 3600)
    
    # Reset Cause (u8) = 0
    rst_cause = struct.pack("B", 0)
    
    # Task Count (u8) = 0 (To keep packet short and simple)
    task_count = struct.pack("B", 0)
    
    payload = (
        header + 
        submodule + 
        queue + 
        inst_count + 
        ts + 
        fsm + 
        resets + 
        io_err + 
        sys_err + 
        cpu + 
        iram + 
        eram + 
        uptime + 
        rst_cause + 
        task_count
    )
    
    return payload

def main():
    payload = create_valid_packet()
    hex_str = payload.hex()
    
    # Tag packet for the system to recognize it as HEALTH_OBC
    # Usually this is done via the Topic or the wrapper content in OpenC3
    # BUT wait, the `health_consumer` receives JSON from RabbitMQ.
    # Who puts it in RabbitMQ? `ws_ingestor`? Or `bridge-backend`?
    # The `pub.py` publishes via MQTT to `cosmos/telemetry`.
    # `bridge-backend` likely listens to MQTT and forwards to RabbitMQ?
    # Or `ws_ingestor`?
    
    # Looking at `pub.py`: it sends RAW BYTES to MQTT topic `cosmos/telemetry`.
    # We need to send the exact same structure.
    
    print(f"Generated Payload ({len(payload)} bytes): {hex_str}")
    
    client = mqtt.Client(client_id="valid_obc_publisher")
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()
    
    # Publish 
    info = client.publish(TOPIC, payload)
    info.wait_for_publish()
    
    print(f"Published to {TOPIC}. Check logs!")
    client.disconnect()

if __name__ == "__main__":
    main()
