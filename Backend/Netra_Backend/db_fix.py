import os
import sys
import psycopg2
from psycopg2 import sql

# Set default env vars for local execution if not set, matching docker-compose
if "DB_USER" not in os.environ:
    os.environ["DB_USER"] = "root"
if "DB_PASSWORD" not in os.environ:
    os.environ["DB_PASSWORD"] = "root"
if "DB_NAME" not in os.environ:
    os.environ["DB_NAME"] = "centraDB"
if "DB_HOST" not in os.environ:
    os.environ["DB_HOST"] = "127.0.0.1"

# Try to import PostgresClient from local file to reuse connection logic
sys.path.append(os.getcwd())

# Attempt imports assuming we are in Backend/Netra_Backend/
# If running via docker composite exec, PYTHONPATH might be set correctly to include netra_backend package
try:
    from netra_backend.db_client import PostgresClient
except ImportError:
    try:
        from db_client import PostgresClient
    except ImportError:
        print("Could not import PostgresClient. Ensure you are in the directory containing netra_backend package or db_client.py")
        sys.exit(1)

def fix_table(conn, table_name):
    print(f"Checking table: {table_name}")
    with conn.cursor() as cur:
        # 1. Check ID column default
        cur.execute(f"""
            SELECT column_default 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' AND column_name = 'id';
        """)
        row = cur.fetchone()
        if row and row[0] is None:
            print(f"  [FIX] 'id' column has no default. Adding sequence...")
            # Create sequence and attach
            seq_name = f"{table_name}_id_seq"
            try:
                # We use safe execution with strings, assuming table_name is trusted (it comes from DB)
                cur.execute(sql.SQL("CREATE SEQUENCE IF NOT EXISTS {}").format(sql.Identifier(seq_name)))
                
                # IMPORTANT: We must double-quote the sequence name INSIDE the string passed to nextval
                # because we created it as a case-sensitive identifier.
                # sql.Literal(seq_name) -> 'HEALTH_OBC_id_seq' (postgres lowercases this content to health_obc_id_seq)
                # sql.Literal(f'"{seq_name}"') -> '"HEALTH_OBC_id_seq"' (postgres respects quotes)
                nextval_arg = f'"{seq_name}"'
                
                cur.execute(sql.SQL("ALTER TABLE {} ALTER COLUMN id SET DEFAULT nextval({})").format(
                    sql.Identifier(table_name), sql.Literal(nextval_arg)
                ))
                # Optional: Make seq owned by column
                cur.execute(sql.SQL("ALTER SEQUENCE {} OWNED BY {}.id").format(
                    sql.Identifier(seq_name), sql.Identifier(table_name)
                ))
                print(f"  [SUCCESS] Added default sequence for 'id'.")
            except Exception as e:
                print(f"  [ERROR] Failed to set id default: {e}")
                conn.rollback()
                return
        elif row:
             print(f"  [OK] 'id' already has default: {row[0]}")
        else:
             print(f"  [SKIP] 'id' column not found.")

        # 2. Check created_at column default
        cur.execute(f"""
            SELECT column_default 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' AND column_name = 'created_at';
        """)
        row = cur.fetchone()
        if row and row[0] is None:
             print(f"  [FIX] 'created_at' has no default. Setting to NOW()...")
             try:
                 cur.execute(sql.SQL("ALTER TABLE {} ALTER COLUMN created_at SET DEFAULT NOW()").format(
                     sql.Identifier(table_name)
                 ))
                 print(f"  [SUCCESS] Set default for 'created_at'.")
             except Exception as e:
                 print(f"  [ERROR] Failed to set created_at default: {e}")
                 conn.rollback()
                 return
        elif row:
             print(f"  [OK] 'created_at' already has default: {row[0]}")
        else:
             print(f"  [SKIP] 'created_at' column not found.")

        # 3. Backfill NULL created_at
        try:
            cur.execute(sql.SQL("UPDATE {} SET created_at = NOW() WHERE created_at IS NULL").format(
                sql.Identifier(table_name)
            ))
            if cur.rowcount > 0:
                print(f"  [UPDATE] Backfilled {cur.rowcount} rows with NULL created_at.")
        except Exception as e:
            print(f"  [ERROR] Failed to backfill created_at: {e}")

        # 4. Backfill NULL id
        # Now that we've ensured a default exists (nextval), we can backfill existing NULLs using that default.
        try:
            cur.execute(sql.SQL("UPDATE {} SET id = DEFAULT WHERE id IS NULL").format(
                sql.Identifier(table_name)
            ))
            if cur.rowcount > 0:
                print(f"  [UPDATE] Backfilled {cur.rowcount} rows with NULL id.")
        except Exception as e:
             print(f"  [ERROR] Failed to backfill id: {e}")

    conn.commit()

def main():
    print("Connecting to DB...")
    
    # Debugging environment - verify what we are using
    # print(f"DB_USER={os.environ.get('DB_USER')}")
    
    try:
        client = PostgresClient()
        conn = client.conn
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # Find all HEALTH_ tables
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name LIKE 'HEALTH_%' AND table_schema = 'public';
        """)
        tables = [row[0] for row in cur.fetchall()]

    print(f"Found {len(tables)} HEALTH tables.")
    for table in tables:
        fix_table(conn, table)
    
    # Also check decoder error tables just in case
    fix_table(conn, "DECODER_FAILED")
    fix_table(conn, "DECODER_NOT_FOUND")

    print("\nDone.")

if __name__ == "__main__":
    main()
