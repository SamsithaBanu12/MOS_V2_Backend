import paho.mqtt.client as mqtt
BROKER_HOST = "127.0.0.1"   # change if your broker is on another machine
BROKER_PORT = 2147
TOPIC = "cosmos/telemetry"
HEX_STR="8c c5 73 00 a5 aa f0 22 7c 79 69 75 07 00 00 81 00 04 6d 02 01 01 ff ff 68 01 00 00 01 00 7b 7b 79 69 00 00 00 00 94 22 1b 4c 94 22 00 00 1b 4c 01 00 ab ea fa 05 16 01 01 00 00 00 01 00 01 01 01 00 00 00 00 00 00 01 00 01 01 00 01 31 01 d7 00 09 05 09 05 00 18 34 34 01 00 00 00 01 00 00 00 01 00 01 00 01 00 01 00 2e 01 02 00 01 00 01 00 01 00 02 00 04 00 04 00 06 00 c4 00 06 00 04 00 01 00 05 00 06 06 06 06 06 7a 00 79 00 79 00 1d 01 35 01 37 01 ed ff 18 18 18 18 17 17 17 17 18 17 1a 17 18 17 18 16 18 18 17 18 17 17 16 17  8d 21 80 34 86 00 00 00 00 01 00 01 00 00 00 02 00 00 00 01 00 05 00 00 00 01 00 01 00 00 00 00 00 64 00 02 00 00 00 02 00 00 00 02 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 1c 00 00 00 08 00 0b 00 02 00 00 00 01 00 00 00 1f 00 01 00 02  00 00 00 00 00 01 00 00 00 00 00 01 00 01 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 e3 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 e4 c3 58 3d e0 88 63 79 83 21 a6 15 74 93 66 cb d0 81 9b 1b 79 d4 cc 78 d6 00 ac 5b 0f 1c c3 92 67 ba"

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