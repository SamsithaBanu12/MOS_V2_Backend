import os
import sys
import datetime

# Setup environment to match Docker
if "DB_USER" not in os.environ:
    os.environ["DB_USER"] = "root"
if "DB_PASSWORD" not in os.environ:
    os.environ["DB_PASSWORD"] = "root"
if "DB_NAME" not in os.environ:
    os.environ["DB_NAME"] = "centraDB"
if "DB_HOST" not in os.environ:
    os.environ["DB_HOST"] = "127.0.0.1"

sys.path.append(os.getcwd())

try:
    from netra_backend.db_client import PostgresClient
except ImportError:
    try:
        from db_client import PostgresClient
    except ImportError:
        print("Could not import PostgresClient.")
        sys.exit(1)

def main():
    print("Initializing PostgresClient...")
    try:
        db = PostgresClient()
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    table_name = "HEALTH_OBC"
    
    # Dummy row that mimics the structure of HEALTH_OBC
    # based on the decoder file we saw earlier
    dummy_row = {
        "Submodule_ID": 1,
        "Queue_ID": 1,
        "Number_of_Instances": 1,
        "Timestamp": "2024-01-01 12:00:00",
        "FSM_State_Code": 0,
        "FSM_State": "TEST_STATE",
        "Reset_Cause_Code": 0,
        "Reset_Cause": "TEST_RESET",
        "Task_Count": 5,
        "Parse_Error": None,
        # Just adding one task status for test
        "Task_01_Status": "SUCCESS" 
    }

    print(f"Attempting to ensure table '{table_name}' exists...")
    try:
        # verify if it exists first
        with db.conn.cursor() as cur:
            cur.execute(f"SELECT to_regclass('public.\"{table_name}\"')")
            res = cur.fetchone()[0]
            if res:
                print(f"Table '{table_name}' ALREADY EXISTS in the DB.")
            else:
                print(f"Table '{table_name}' DOES NOT exist. Code should create it.")

        db.ensure_table_for_packet(table_name, dummy_row)
        print("ensure_table_for_packet call finished.")
        
        # Verify creation
        with db.conn.cursor() as cur:
            cur.execute(f"SELECT to_regclass('public.\"{table_name}\"')")
            res = cur.fetchone()[0]
            if res:
                print(f"SUCCESS: Table '{table_name}' now exists.")
                
                # Verify columns
                cur.execute(f"""
                    SELECT column_name, column_default 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}' AND column_name IN ('id', 'created_at')
                """)
                rows = cur.fetchall()
                print("Columns check:")
                for r in rows:
                    print(f"  {r}")
            else:
                print(f"FAILURE: Table '{table_name}' was NOT created.")
                
    except Exception as e:
        print(f"Error during creation test: {e}")

if __name__ == "__main__":
    main()
