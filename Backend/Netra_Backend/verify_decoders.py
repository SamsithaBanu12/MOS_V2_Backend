import importlib
import sys
import os

# Add current dir to path so we can import netra_backend provided we are running from Backend/Netra_Backend
sys.path.append(os.getcwd())

from netra_backend.config import get_openc3_config

def main():
    print("Verifying decoders...")
    try:
        config = get_openc3_config()
        packets = config.packets_tlm
    except Exception as e:
        print(f"Failed to load config: {e}")
        return

    health_packets = [p for p in packets if "__HEALTH_" in p]
    print(f"Found {len(health_packets)} health packets.")

    failed = []
    
    for pkt_full in health_packets:
        parts = pkt_full.split("__")
        if len(parts) < 4:
            print(f"Skipping weird packet: {pkt_full}")
            continue
            
        core_name = "__".join(parts[3:])
        module_name = f"netra_backend.health_decoders.{core_name}"
        
        try:
            importlib.import_module(module_name)
            # print(f"OK: {core_name}")
        except Exception as e:
            print(f"FAIL (EXCEPTION): {core_name} -> {e}")
            failed.append(core_name)
        except BaseException as e: # Catch SyntaxError, etc.
            print(f"FAIL (BASE EXCEPTION): {core_name} -> {type(e).__name__}: {e}")
            failed.append(core_name)

    print(f"\nVerification Complete. {len(failed)} failures.")
    if failed:
        print("Failed decoders:", failed)

if __name__ == "__main__":
    main()
