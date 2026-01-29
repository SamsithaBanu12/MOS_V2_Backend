
import sys
import os

# Add path to find netra_backend
sys.path.append(os.getcwd())

# We need to import the decoder function.
# Assuming we are in Backend/ not Backend/Netra_Backend
# But user context says active docs are in Backend/Netra_Backend.
# Let's assume we run this from Backend/Netra_Backend/

try:
    from netra_backend.health_decoders.HEALTH_OBC import HEALTH_OBC
except ImportError:
    # Try local import if running inside the decoders dir or similar
    try:
        from health_decoders.HEALTH_OBC import HEALTH_OBC
    except ImportError:
        print("Could not import HEALTH_OBC. Adjust python path.")
        sys.exit(1)

HEX_STR=" 8c c5 76 00 a5 aa f0 6f 9d 5b 69 48 00 00 00 81 00 04 6d 02 01 01 ff ff 04 00 05 00 00 00 39 2e 09 34 d5 a2 28 1e a4 ef 4d 2f 40 5c c3 cf a9 e4 82 62 34 5b 0e bd eb d1 2c f1 a0 cb 2d 94 40 ba"

print(f"Testing Decoder with HEX_STR (len={len(HEX_STR.replace(' ', ''))//2} bytes)")

try:
    # Temporarily monkey-patch the decoder or valid function to print internal values?
    # Or just copy the start of the logic here for debugging:
    def debug_header(hex_str):
        buf = bytes.fromhex(hex_str.replace(" ", ""))
        pos = 0
        print(f"Total length: {len(buf)}")
        
        # 1) Header
        header = buf[:26]
        print(f"Header (26 bytes): {header.hex(' ')}")
        pos += 26
        
        # 2) Submodule
        submodule_id = buf[pos]
        pos += 1
        print(f"Submodule ID: {submodule_id}")
        
        # 3) Queue
        queue_id = buf[pos]
        pos += 1
        print(f"Queue ID: {queue_id}")
        
        # 4) Instances
        inst_count = int.from_bytes(buf[pos:pos+2], "little")
        print(f"Instance Count (raw bytes {buf[pos:pos+2].hex()}): {inst_count}")
        pos += 2
        
        return inst_count

    print("-" * 20)
    print("DEBUG PARSING:")
    count = debug_header(HEX_STR)
    print("-" * 20)
    
    segments = HEALTH_OBC(HEX_STR)
    print(f"Result segments: {segments}")
    print(f"Count: {len(segments)}")
except Exception as e:
    print(f"Decoder raised exception: {e}")
