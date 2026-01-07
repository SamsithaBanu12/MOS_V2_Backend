# encryption.py
import hashlib
from Crypto.Cipher import AES

KEY_HEX = "754272407753446f542d5f6a4c74515e4e24363041333555504f4d77543d5774"

def encrypt_frame(frame_hex: str) -> str:
    frame_hex = frame_hex.replace(" ", "").lower()

    # Fixed fields
    csp = frame_hex[0:8]
    hmac = frame_hex[-66:-2]
    eof = frame_hex[-2:]
    payload_crc_hex = frame_hex[8:-66]
    payload = bytes.fromhex(payload_crc_hex)

    # Extract fields
    timestamp = payload[3:7]
    seq = payload[7:9]                  # 2 bytes LE
    sat_id = payload[9:10]
    src_id = payload[12:13]
    dest_id = payload[13:14]
    tc_id = payload[15:17]
    tc_len_le = payload[19:21]
    tc_len = int.from_bytes(tc_len_le, "little")

    # Locate TC data
    tc_data_start = 21
    tc_data_end = tc_data_start + tc_len
    crc_index = tc_data_end

    encrypt_region = payload[tc_data_start : crc_index + 1]

    # Nonce input construction
    nonce_input = (
        timestamp +
        seq +
        src_id + b"\x00" +
        dest_id + b"\x00" +
        tc_id +
        sat_id + b"\x00"
    )

    digest = hashlib.sha256(nonce_input).digest()

    # NEW LOGIC FOR SEQUENCE NUMBER (2-byte little endian)
    seq_le = seq[::-1]                     # reverse LE -> BE
    seq_val = int.from_bytes(seq_le, "big")

    # even → first 16 bytes, odd → last 16 bytes
    if seq_val % 2 == 0:
        nonce_bytes = digest[:16]
    else:
        nonce_bytes = digest[16:]

    key = bytes.fromhex(KEY_HEX)
    init_val = int.from_bytes(nonce_bytes, "big")
    cipher = AES.new(key, AES.MODE_CTR, nonce=b"", initial_value=init_val)

    encrypted = cipher.encrypt(encrypt_region)
    encrypted_hex = encrypted.hex()

    # Build new payload
    new_payload_hex = (
        payload[:tc_data_start].hex() +
        encrypted_hex +
        payload[crc_index + 1:].hex()
    )

    final_hex = csp + new_payload_hex + hmac + eof
    return final_hex.lower()
