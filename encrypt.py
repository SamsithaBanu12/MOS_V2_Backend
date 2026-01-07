
# encrypt_frame_cli.py
import hashlib
from Crypto.Cipher import AES

KEY_HEX = "754272407753446f542d5f6a4c74515e4e24363041333555504f4d77543d5774"

def encrypt_frame(frame_hex: str) -> str:
    frame_hex = frame_hex.replace(" ", "").lower()

    # Fixed frame fields
    csp = frame_hex[0:8]
    hmac = frame_hex[-66:-2]
    eof = frame_hex[-2:]

    payload_hex = frame_hex[8:-66]
    payload = bytes.fromhex(payload_hex)

    # Extract fields
    timestamp = payload[3:7]
    seq = payload[7:9]              # 2 bytes little-endian
    sat_id = payload[9:10]
    src_id = payload[12:13]
    dest_id = payload[13:14]
    tc_id = payload[15:17]

    tc_len = int.from_bytes(payload[19:21], "little")

    # TC data region
    tc_data_start = 21
    tc_data_end = tc_data_start + tc_len
    encrypt_region = payload[tc_data_start:tc_data_end + 1]

    # Nonce input
    nonce_input = (
        timestamp +
        seq +
        src_id + b"\x00" +
        dest_id + b"\x00" +
        tc_id +
        sat_id + b"\x00"
    )

    digest = hashlib.sha256(nonce_input).digest()

    # Sequence parity
    seq_val = int.from_bytes(seq, "little")
    nonce_bytes = digest[:16] if seq_val % 2 == 0 else digest[16:]

    # AES-CTR encryption
    key = bytes.fromhex(KEY_HEX)
    init_val = int.from_bytes(nonce_bytes, "big")
    cipher = AES.new(key, AES.MODE_CTR, nonce=b"", initial_value=init_val)

    encrypted_region = cipher.encrypt(encrypt_region)

    # Rebuild payload
    new_payload_hex = (
        payload[:tc_data_start].hex() +
        encrypted_region.hex() +
        payload[tc_data_end + 1:].hex()
    )

    return (csp + new_payload_hex + hmac + eof).lower()


if __name__ == "__main__":
    print("Enter frame hex string:")
    input_hex = input().strip()

    try:
        encrypted_hex = encrypt_frame(input_hex)
        print("\nEncrypted frame:")
        print(encrypted_hex)
    except Exception as e:
        print("Error:", e)
