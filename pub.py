import paho.mqtt.client as mqtt
import time

BROKER_HOST = "127.0.0.1"   # change if your broker is on another machine
BROKER_PORT = 2147
TOPIC = "cosmos/telemetry"

# Array of hex strings to be assessed for generating alerts
HEX_STRINGS = [
    "8c c5 7f 00 a5 aa f0 a2 c2 60 69 27 00 00 00 81 00 04 6d 02 01 01 ff ff ec 00 01 1e 08 00 00 df c2 60 69 9a 92 41 f9 5d 92 a8 40 d3 d4 20 e8 6b c1 ac 40 49 d3 6a 35 7d f3 b1 c0 00 ea c2 60 69 70 af 80 de 9a 10 a8 40 f0 22 7b 6f c1 0f ad 40 9d df f2 47 d9 ff b1 c0 00 f4 c2 60 69 7c a8 6c c8 12 8e a7 40 be 1d 6f 16 37 5d ad 40 40 b4 9a 36 8a 0b b2 c0 00 01 c3 60 69 fc 09 85 80 63 ec a6 40 e1 f0 02 b2 55 bb ad 40 40 9e fe 3e 02 19 b2 c0 00 0b c3 60 69 cd 90 6a a5 c0 6a a6 40 e2 70 18 5e 5d 05 ae 40 1a b2 18 52 03 23 b2 c0 00 16 c3 60 69 ae 77 24 54 de e5 a5 40 db ab 5d d9 f2 4f ae 40 06 84 60 d3 8b 2c b2 c0 00 20 c3 60 69 e4 63 24 08 4a 60 a5 40 fe 19 b5 d9 9d 99 ae 40 bc e8 0a 89 67 35 b2 c0 00 2a c3 60 69 ad e2 d7 52 08 da a4 40 ac 7c 72 ec 5b e2 ae 40 f6 57 1d 1f 96 3d b2 c0 8a 3d 20 1f 30 14 df b3 85 06 61 76 01 a7 76 d5 5f 50 2a 19 10 58 46 4d c6 55 49 44 96 65 5c a0 66 ba",
    "8c c5 7e 00 a5 aa f0 a2 c2 60 69 0c 00 00 00 81 00 04 6d 02 01 01 ff ff 5c 00 01 07 08 00 00 df c2 60 69 02 00 18 fc 00 00 00 ea c2 60 69 02 00 18 fc ff ff 00 f4 c2 60 69 02 00 18 fc ff ff 00 01 c3 60 69 02 00 18 fc fe ff 00 0b c3 60 69 02 00 18 fc fe ff 00 16 c3 60 69 02 00 18 fc fe ff 00 20 c3 60 69 03 00 18 fc fd ff 00 2a c3 60 69 03 00 18 fc fc ff f4 b3 b8 a7 1c 07 a6 49 e4 f6 43 2d a9 17 61 a2 f5 15 fc 3b 94 f7 9c 58 d8 29 a4 3e ed 27 3c 88 65 ba",
    "8c c5 7c 00 a5 aa f0 a2 c2 60 69 24 00 00 00 81 00 04 6d 02 01 01 ff ff 5c 00 01 1c 08 00 00 df c2 60 69 00 00 00 00 00 00 00 ea c2 60 69 00 00 00 00 00 00 00 f4 c2 60 69 00 00 00 00 00 00 00 01 c3 60 69 00 00 00 00 00 00 00 0b c3 60 69 00 00 00 00 00 00 00 16 c3 60 69 00 00 00 00 00 00 00 20 c3 60 69 00 00 00 00 00 00 00 2a c3 60 69 00 00 00 00 00 00 89 db ab 68 80 90 01 c4 b9 39 8e a8 4d 8b a5 e0 4a c1 50 e1 32 34 a3 73 77 5e 94 5d 59 3d 40 58 f5 ba",
    "8c c5 7a 00 a5 aa f0 a2 c2 60 69 22 00 00 00 81 00 04 6d 02 01 01 ff ff 5c 00 01 0e 08 00 00 df c2 60 69 6a f5 ab 06 38 03 00 ea c2 60 69 72 f5 9d 06 f7 03 00 f4 c2 60 69 88 f5 90 06 b9 04 00 01 c3 60 69 b5 f5 7e 06 a6 05 00 0b c3 60 69 ea f5 6e 06 69 06 00 16 c3 60 69 2d f6 5e 06 2c 07 00 20 c3 60 69 80 f6 4e 06 ec 07 00 2a c3 60 69 e1 f6 3e 06 ab 08 57 12 6b 52 cd 07 54 ea 5e 5d da 14 ca 53 13 b4 6f 3f 37 35 ba f7 d2 bc fe 1e 66 36 3e f8 fd 3d 85 ba",
    "8c c5 74 00 a5 aa f0 a2 c2 60 69 1c 00 00 00 81 00 04 6d 02 01 01 ff ff 74 00 01 17 08 00 00 df c2 60 69 03 b6 01 fd fe 2c 00 f8 fe 00 ea c2 60 69 03 ab 01 01 ff 22 00 fa fe 00 f4 c2 60 69 03 9f 01 05 ff 19 00 fb fe 00 01 c3 60 69 03 8e 01 0c ff 0c 00 fe fe 00 0b c3 60 69 03 80 01 13 ff 03 00 00 ff 00 16 c3 60 69 03 71 01 1b ff fa ff 03 ff 00 20 c3 60 69 03 5f 01 24 ff ef ff 05 ff 00 2a c3 60 69 03 4f 01 2e ff e6 ff 08 ff 13 6f de fe 0e da d4 a7 a3 0b 87 9e 14 1c 9b 82 e3 61 bb 01 9b 0e 4b cb dc f0 f6 0f db 66 31 16 b5 ba",

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