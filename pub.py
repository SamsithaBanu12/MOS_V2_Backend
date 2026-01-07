import paho.mqtt.client as mqtt
BROKER_HOST = "127.0.0.1"   # change if your broker is on another machine
BROKER_PORT = 2147
TOPIC = "cosmos/telemetry"
HEX_STR=" 8c c5 78 00 a5 aa f0 12 ff 26 69 3b 01 00 00 81 00 04 6d 02 01 01 ff ff 14 00 04 04 02 00 00 00 0b 42 23 fe 26 69 00 00 09 42 9b fe 26 69 8d da 40 ad a9 4a 31 90 7a 46 1e 8b 72 51 0b e4 ef 6c e7 77 15 50 56 23 cb 44 77 43 e2 41 13 2a a0 ba"

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