import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def init_database():
    # Load configuration from environment variables or use defaults
    DB_HOST = os.getenv("DB_HOST", "db")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASS = os.getenv("DB_PASSWORD", "root")
    DB_NAME = os.getenv("DB_NAME", "centraDB")

    print(f"--- Starting Database Initialization ---")
    print(f"Target: {DB_HOST}:{DB_PORT} as User: {DB_USER}")

    conn = None
    try:
        # 1. Connect to the default 'postgres' database to create our target database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            dbname="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # 2. Check if the database exists
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        exists = cur.fetchone()

        if not exists:
            print(f"Database '{DB_NAME}' does not exist. Creating...")
            cur.execute(f'CREATE DATABASE "{DB_NAME}"')
            print(f"Database '{DB_NAME}' created successfully. ✅")
        else:
            print(f"Database '{DB_NAME}' already exists. Skipping creation. ✅")

        cur.close()
        conn.close()

        # 3. Connect to the newly created (or existing) database to create the table
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            dbname=DB_NAME
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        print(f"Creating 'alerts' table in '{DB_NAME}' if it doesn't exist...")
        create_table_query = """
        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,
            timestamp VARCHAR(255),
            engine_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            submodule_name VARCHAR(255),
            submodule_id VARCHAR(255),
            metric VARCHAR(255),
            value FLOAT,
            min_limit FLOAT,
            max_limit FLOAT,
            severity VARCHAR(50),
            reason TEXT,
            packet_raw VARCHAR(255),
            packet_matched VARCHAR(255),
            status VARCHAR(50) DEFAULT 'alert_identified'
        );
        """
        cur.execute(create_table_query)
        print(f"Table 'alerts' verified/created successfully. ✅")

        cur.close()
        print(f"--- Initialization Complete! ---")

    except Exception as e:
        print(f"Error during database initialization: {e}")
        print("\nPossible reasons:")
        print("1. PostgreSQL is not running on the target host.")
        print("2. The user 'root' does not exist or has no permission to create databases.")
        print("3. Network/Firewall settings are blocking the connection.")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    init_database()