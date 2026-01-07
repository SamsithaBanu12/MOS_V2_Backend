
import csv
import psycopg2
import os

# Database Configuration
HOST = os.getenv("DB_HOST", "localhost")
PORT = os.getenv("DB_PORT", "5432")
DBNAME = os.getenv("DB_NAME", "centraDB")
USER = os.getenv("DB_USER", "root")
PASSWORD = os.getenv("DB_PASSWORD", "root")

# File Paths (Absolute paths required)
# Adjust these paths to match the actual location of your CSV files
EPS_CSV_PATH = r"_Health_EPS.csv_"
OBC_CSV_PATH = r"_Health_OBC.csv_"

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=HOST,
            port=PORT,
            dbname=DBNAME,
            user=USER,
            password=PASSWORD
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def determine_column_types(rows):
    if not rows:
        return []

    num_cols = len(rows[0])
    col_types = []

    for i in range(num_cols):
        is_bool = True
        is_int = True
        is_float = True

        for row in rows:
            val = row[i]
            if not val:
                continue
            
            # Check Boolean
            if val.lower() not in ('t', 'f', 'true', 'false'):
                is_bool = False
            
            # Check Integer
            if is_int:
                try:
                    int(val)
                except ValueError:
                    is_int = False
            
            # Check Float
            if is_float:
                try:
                    float(val)
                except ValueError:
                    is_float = False
        
        if is_bool:
            col_types.append("BOOLEAN")
        elif is_int:
            col_types.append("INTEGER")
        elif is_float:
            col_types.append("FLOAT")
        else:
            col_types.append("TEXT")
            
    return col_types

def create_table_from_csv(cursor, table_name, csv_path):
    print(f"Processing {csv_path} for table {table_name}...")
    
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return

    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            print(f"Empty CSV file: {csv_path}")
            return
        
        # Read all rows to memory for type inference
        rows = list(reader)
        
        if not rows:
            print(f"No data in CSV file: {csv_path}")
            return

        col_types = determine_column_types(rows)
        
        # Build CREATE TABLE query
        columns_def = []
        for header, col_type in zip(headers, col_types):
             # Clean header name
            safe_header = header.replace(' ', '_').replace('-', '_').replace('.', '_').replace('/', '_')
            columns_def.append(f'"{safe_header}" {col_type}')
            
        create_query = f"""
        CREATE TABLE IF NOT EXISTS "{table_name}" (
            {', '.join(columns_def)}
        );
        """
        cursor.execute(create_query)
        
        # Prepare data for insertion
        insert_query = f"""
        INSERT INTO "{table_name}" ({', '.join([f'"{h}"' for h in headers])})
        VALUES ({', '.join(['%s'] * len(headers))})
        """
        
        clean_rows = []
        for row in rows:
            clean_row = []
            for item in row:
                if item == 't':
                    clean_row.append(True)
                elif item == 'f':
                    clean_row.append(False)
                elif item == '':
                    clean_row.append(None)
                else:
                    clean_row.append(item)
            clean_rows.append(clean_row)

        cursor.executemany(insert_query, clean_rows)
        print(f"Inserted {len(clean_rows)} rows into {table_name}.")


def main():
    conn = get_db_connection()
    if not conn:
        return

    try:
        cur = conn.cursor()
        
        create_table_from_csv(cur, "HEALTH_EPS", EPS_CSV_PATH)
        create_table_from_csv(cur, "HEALTH_OBC", OBC_CSV_PATH)

        conn.commit()
        print("Data import successful.")
        
    except Exception as e:
        conn.rollback()
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
