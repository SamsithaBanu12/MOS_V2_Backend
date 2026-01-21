import paho.mqtt.client as mqtt
BROKER_HOST = "127.0.0.1"   # change if your broker is on another machine
BROKER_PORT = 2147
TOPIC = "cosmos/telemetry"
HEX_STR="8cc57f00a5aaf0a2c26069270000008100046d020101ffffec00011e080000dfc260699a9241f95d92a840d3d420e86bc1ac4049d36a357df3b1c000eac2606970af80de9a10a840f0227b6fc10fad409ddff247d9ffb1c000f4c260697ca86cc8128ea740be1d6f16375dad4040b49a368a0bb2c00001c36069fc09858063eca640e1f002b255bbad40409efe3e0219b2c0000bc36069cd906aa5c06aa640e270185e5d05ae401ab218520323b2c00016c36069ae772454dee5a540dbab5dd9f24fae40068460d38b2cb2c00020c36069e46324084a60a540fe19b5d99d99ae40bce80a896735b2c0002ac36069ade2d75208daa440ac7c72ec5be2ae40f6571d1f963db2c08a3d201f3014dfb38506617601a776d55f502a191058464dc655494496655ca066ba"

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