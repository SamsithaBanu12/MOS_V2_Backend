import paho.mqtt.client as mqtt
BROKER_HOST = "127.0.0.1"   # change if your broker is on another machine
BROKER_PORT = 2147
TOPIC = "cosmos/telemetry"
HEX_STR="8c c5 76 00 a5 aa f0 a2 c2 60 69 1e 00 00 00 81 00 04 6d 02 01 01 ff ff 5c 00 01 19 08 00 00 df c2 60 69 96 00 2c 00 96 00 00 ea c2 60 69 96 00 2c 00 96 00 00 f4 c2 60 69 96 00 2c 00 96 00 00 01 c3 60 69 96 00 2a 00 96 00 00 0b c3 60 69 96 00 28 00 96 00 00 16 c3 60 69 96 00 28 00 96 00 00 20 c3 60 69 96 00 24 00 96 00 00 2a c3 60 69 96 00 22 00 96 00 a2 9e 79 f8 b7 f1 a0 57 cc 3d 17 1c 20 06 99 47 1e 50 87 30 8f 4a 48 d2 55 0b 84 69 99 8c 9a 44 3a ba"

def main():
    # Convert hex string to raw bytes
    payload = bytes.fromhex(HEX_STR)
    client = mqtt.Client(client_id="cosmos_telemetry_publisher")
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    # Publish and make sure it’s sent before exiting
    result = client.publish(TOPIC, payload)
    result.wait_for_publish()
    client.disconnect()
    print(f"Published {len(payload)} bytes to '{TOPIC}' on {BROKER_HOST}:{BROKER_PORT}")
if __name__ == "__main__":
    main()