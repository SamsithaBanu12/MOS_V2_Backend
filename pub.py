import paho.mqtt.client as mqtt
BROKER_HOST = "127.0.0.1"   # change if your broker is on another machine
BROKER_PORT = 2147
TOPIC = "cosmos/telemetry"
HEX_STR="8c c5 7b 00 a5 aa f0 a2 c2 60 69 23 00 00 00 81 00 04 6d 02 01 01 ff ff 5c 00 01 1b 08 00 00 df c2 60 69 00 00 00 00 00 00 00 ea c2 60 69 00 00 00 00 00 00 00 f4 c2 60 69 00 00 00 00 00 00 00 01 c3 60 69 00 00 00 00 00 00 00 0b c3 60 69 00 00 00 00 00 00 00 16 c3 60 69 00 00 00 00 00 00 00 20 c3 60 69 00 00 00 00 00 00 00 2a c3 60 69 00 00 00 00 00 00 10 9d dd b1 25 48 95 fd 26 ad 5f 88 0a a6 b4 a1 3a b8 45 f7 6b 27 97 68 05 04 b2 26 3c c1 29 29 b2 ba"

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