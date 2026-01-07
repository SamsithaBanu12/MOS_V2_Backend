import hashlib
from Crypto.Cipher import AES

# Key for extended header data == 0
KEY0_HEX = "754272407753446f542d5f6a4c74515e4e24363041333555504f4d77543d5774"

# Key for extended header data == 1
KEY1_HEX = "552451675E6F5E6771456C535E78652665517850623365723643264768266A6D"

# Backwards-compatible default (same as old KEY_HEX)
KEY_HEX = KEY0_HEX


def _derive_tm_nonce(payload: bytes) -> bytes:
    """
    Derive the 16-byte nonce for TM frames, using the same algorithm
    and fields as encryption, just with TM offsets.
    
    TM payload layout (after CSP header):
      0   : SOF1 (1)
      1   : SOF2 (1)
      2   : TM CTRL (1)
      3-6 : Timestamp (4)
      7-8 : Sequence number (2, little endian)
      9   : SAT Id (1)
      10  : QoS (1)
      11  : Src ID (1)
      12  : Dest ID (1)
      13  : RM id (1)
      14-15: TM ID (2)
      16  : Extended header len (1)
      17  : Extended header data (1)
      18-19: CO ID (2)
      20-21: TM Len (2, little endian)
      22..: TM Data (tm_len bytes)
      ... : CRC (1)
      ... : Auth bytes (32) – outside encrypted region
    """

    # Same fields as encryption, adjusted offsets for TM
    timestamp = payload[3:7]      # 4 bytes
    seq = payload[7:9]            # 2 bytes (little endian)
    sat_id = payload[9:10]        # 1 byte
    src_id = payload[11:12]       # 1 byte
    dest_id = payload[12:13]      # 1 byte
    tm_id = payload[14:16]        # 2 bytes

    # Same construction as encryption: append \x00 between certain fields
    nonce_input = (
        timestamp +
        seq +
        src_id + b"\x00" +
        dest_id + b"\x00" +
        tm_id +
        sat_id + b"\x00"
    )

    digest = hashlib.sha256(nonce_input).digest()

    # Sequence is stored little-endian; convert to integer
    seq_le = seq[::-1]                 # LE -> BE
    seq_val = int.from_bytes(seq_le, "big")

    # even → first 16 bytes, odd → last 16 bytes (same rule as encryption)
    if seq_val % 2 == 0:
        nonce_bytes = digest[:16]
    else:
        nonce_bytes = digest[16:]

    return nonce_bytes


def decrypt_tm_frame(frame_hex: str, key_hex: str = KEY_HEX) -> str:
    """
    Decrypts the TM Data + CRC region of an encrypted TM frame (CTR mode)
    and returns the full frame as a hex string with decrypted content.

    Input:  'frame_hex' – full frame, same format as used in encryption.
    Output: decrypted frame hex string (same length).

    NOTE: By default, the key is chosen based on the 'extended header data'
          field (byte 17 of the payload):
            - 0 → KEY0_HEX
            - 1 → KEY1_HEX
          If 'key_hex' is explicitly passed, that overrides this behaviour.
    """
    # Normalise: remove spaces, make lowercase
    frame_hex = frame_hex.replace(" ", "").lower()

    # Split outer structure
    csp = frame_hex[0:8]        # 4 bytes CSP header
    hmac = frame_hex[-66:-2]    # 32 bytes authenticated/HMAC
    eof = frame_hex[-2:]        # 1 byte EOF

    # Everything between CSP and HMAC is 'payload' (SOF1...CRC...)
    payload_hex = frame_hex[8:-66]
    payload = bytes.fromhex(payload_hex)

    # --- Locate TM Data and CRC based on TM frame format ---

    # TM Len is 2 bytes little-endian at byte indices 20–21 in payload
    tm_len_le = payload[20:22]
    tm_len = int.from_bytes(tm_len_le, "little")

    tm_data_start = 22
    tm_data_end = tm_data_start + tm_len  # index AFTER last TM data byte
    crc_index = tm_data_end               # CRC is right after TM data

    if crc_index >= len(payload):
        raise ValueError(
            f"TM length ({tm_len}) points outside payload (len={len(payload)})"
        )

    # Encrypted region is TM Data + CRC (exactly like encryption)
    encrypted_region = payload[tm_data_start : crc_index + 1]

    # --- Select key based on extended header data, unless explicitly overridden ---
    if key_hex == KEY_HEX:
        # Extended header data is byte index 17
        extended_hdr_data = payload[17]
        if extended_hdr_data == 0:
            key_hex_to_use = KEY0_HEX
        elif extended_hdr_data == 1:
            key_hex_to_use = KEY1_HEX
        else:
            # Fallback: use default key (KEY0_HEX / KEY_HEX)
            key_hex_to_use = KEY_HEX
    else:
        # Caller explicitly provided key_hex
        key_hex_to_use = key_hex

    # --- Derive nonce (same as encryption) ---
    nonce_bytes = _derive_tm_nonce(payload)

    key = bytes.fromhex(key_hex_to_use)
    init_val = int.from_bytes(nonce_bytes, "big")

    # AES-CTR decryption (encrypt/decrypt are symmetric in CTR)
    cipher = AES.new(key, AES.MODE_CTR, nonce=b"", initial_value=init_val)
    decrypted_region = cipher.decrypt(encrypted_region)

    # --- Rebuild payload with decrypted TM Data + CRC ---
    new_payload = (
        payload[:tm_data_start] +
        decrypted_region +
        payload[crc_index + 1:]
    )

    # --- Rebuild full frame ---
    new_frame_hex = csp + new_payload.hex() + hmac + eof
    return new_frame_hex.lower()
