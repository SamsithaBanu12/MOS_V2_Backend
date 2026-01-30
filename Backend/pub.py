import paho.mqtt.client as mqtt
BROKER_HOST = "127.0.0.1"   # change if your broker is on another machine
BROKER_PORT = 2147
TOPIC = "cosmos/telemetry"
HEX_STR="8c c5 74 00 a5 aa f0 f2 f7 74 67 d9 1d 00 00 81 00 04 6d 02 01 01 ff ff a3 00 05 00 01 00 c6 f7 74 67 00 00 00 00 01 00 00 00 00 fc f2 58 41 00 24 d9 1e 82 61 55 01 3a 07 00 00 00 40 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 e1 6b fd 6a 1c c3 56 33 a7 83 e9 32 e3 bd 6a 1d 20 16 40 0b eb 4f 08 bd 38 5a 45 3d d2 0a 34 5f 3e ba"

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