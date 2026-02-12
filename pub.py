import paho.mqtt.client as mqtt
import time

BROKER_HOST = "127.0.0.1"   # change if your broker is on another machine
BROKER_PORT = 2147
TOPIC = "cosmos/telemetry"

# Array of hex strings to be assessed for generating alerts
HEX_STRINGS = [
    "8c c5 7c 00 a5 aa f0 8c bf 7a 69 3e 02 00 00 81 00 04 6d 02 01 01 ff ff 15 03 05 00 05 00 a6 bd 7a 69 00 00 00 00 03 03 00 00 00 00 00 44 42 70 9c 00 00 c8 b1 1f 00 20 00 00 00 08 3d 00 1e 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 f9 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 01 00 01 00 01 00 00 00 1e be 7a 69 00 00 00 00 03 03 00 00 00 00 00 44 42 98 9b 00 00 48 b3 1f 00 22 00 00 00 08 3d 00 1e 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 25 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 01 00 01 00 01 00 00 00 97 be 7a 69 00 00 00 00 03 03 00 00 00 00 00 44 42 08 9a 00 00 a0 b0 1f 00 24 00 00 00 08 3d 00 1e 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 52 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 01 00 01 00 01 00 00 00 0f bf 7a 69 00 00 00 00 03 03 00 00 00 00 00 44 42 68 94 00 00 70 a7 1f 00 26 00 00 00 08 3d 00 1e 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 7d 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 01 00 01 00 01 00 00 00 87 bf 7a 69 00 00 00 00 03 03 00 00 00 00 00 44 42 68 93 00 00 48 a2 1f 00 28 00 00 00 08 3d 00 1e 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 a9 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 01 00 01 00 01 00 00 00 c3 95 2d 3b 02 01 df 64 f0 60 f8 28 41 70 f0 e9 31 76 c9 86 55 b4 20 29 0a ec f1 87 07 0c 74 de cf ba"
]

def main():
    client = mqtt.Client(client_id="cosmos_telemetry_test_publisher")
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    
    for i, hex_str in enumerate(HEX_STRINGS):
        try:
            # Convert hex string to raw bytes
            payload = bytes.fromhex(hex_str)
            
            # Publish and make sure it’s sent
            result = client.publish(TOPIC, payload)
            result.wait_for_publish()
            
            print(f"[{i+1}/{len(HEX_STRINGS)}] Published {len(payload)} bytes to '{TOPIC}'")
            
            # Small delay between publishes if needed
            time.sleep(0.5) 
            
        except ValueError as e:
            print(f"Error parsing hex string at index {i}: {e}")

    client.disconnect()
    print(f"\nFinished publishing all {len(HEX_STRINGS)} messages to {BROKER_HOST}:{BROKER_PORT}")

if __name__ == "__main__":
    main()