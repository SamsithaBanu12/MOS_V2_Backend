"""
Database utility functions for OD Service.
Handles data fetching and CSV export.
"""

import os
import csv
import sys
import subprocess
from typing import List, Dict, Any
from datetime import datetime
import pytz

# Add parent directory to path to import db module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.db import get_db_connection, Tables
from psycopg2.extras import RealDictCursor


def fetch_data(table_name: str, start_time: str, end_time: str) -> List[Dict[str, Any]]:
    """
    Fetch data from specified table within a time range.
    
    Args:
        table_name: Name of the database table
        start_time: Start timestamp (ISO format)
        end_time: End timestamp (ISO format)
        
    Returns:
        List of dictionaries containing the fetched rows
        
    Raises:
        Exception: If query execution fails
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Using epoch for timestamp filtering (actual measurement timestamp)
        query = f'SELECT * FROM "{table_name}" WHERE epoch >= %s AND epoch <= %s ORDER BY epoch ASC'
        cursor.execute(query, (start_time, end_time))
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        print(f"Error executing query on {table_name}: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def save_tle_data(tle_data: Dict[str, Any]) -> bool:
    """
    Save TLE data to the database with a created_at timestamp.
    
    Args:
        tle_data: Dictionary containing TLE information (name, line1, line2)
        
    Returns:
        True if successful, False otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Ensure table exists
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS "{Tables.TLE}" (
            id SERIAL PRIMARY KEY,
            satellite_name VARCHAR(255) NOT NULL,
            line1 VARCHAR(255) NOT NULL,
            line2 VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
        """
        cursor.execute(create_table_query)
        conn.commit()
        
        # Insert data
        insert_query = f"""
        INSERT INTO "{Tables.TLE}" (satellite_name, line1, line2, created_at)
        VALUES (%s, %s, %s, %s)
        """
        
        current_time = datetime.now(pytz.UTC)
        
        cursor.execute(insert_query, (
            tle_data.get('name', 'Unknown'),
            tle_data.get('line1'),
            tle_data.get('line2'),
            current_time
        ))
        conn.commit()
        print(f"Successfully saved TLE data for {tle_data.get('name', 'Unknown')} at {current_time}")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Error saving TLE data: {e}")
        return False
        
    finally:
        cursor.close()
        conn.close()


def fetch_latest_tle() -> Dict[str, Any]:
    """
    Fetch the most recent TLE data from the database.
    
    Returns:
        Dictionary containing TLE information (name, line1, line2) or None if empty
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        query = f'SELECT * FROM "{Tables.TLE}" ORDER BY created_at DESC LIMIT 1'
        cursor.execute(query)
        row = cursor.fetchone()
        
        if row:
            return {
                "name": row['satellite_name'],
                "line1": row['line1'],
                "line2": row['line2'],
                "created_at": row['created_at']
            }
        return None
    except Exception as e:
        print(f"Error fetching latest TLE: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


def write_measurements_csv(pos_data: List[Dict], vel_data: List[Dict], output_dir: str) -> str:
    """
    Write position and velocity data to measurements.csv in the specified directory.
    Merges data by epoch timestamp. Overwrites existing file.
    
    Args:
        pos_data: List of position data dictionaries
        vel_data: List of velocity data dictionaries
        output_dir: Directory where CSV should be saved
        
    Returns:
        Full path to the created CSV file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    csv_path = os.path.join(output_dir, "utils/OD/OD-Release/measurement.csv")
    
    # Ensure nested directory exists
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    
    # Create a dictionary to merge position and velocity data by epoch
    merged_data = {}
    
    # Add position data
    for row in pos_data:
        epoch = row.get('epoch')
        if epoch:
            # Convert to string if it's a datetime object
            epoch_str = epoch.isoformat() if isinstance(epoch, datetime) else str(epoch)
            merged_data[epoch_str] = {
                'epoch': epoch_str,
                'x': row.get('x'),
                'y': row.get('y'),
                'z': row.get('z'),
                'vx': None,
                'vy': None,
                'vz': None
            }
    
    # Add velocity data
    for row in vel_data:
        epoch = row.get('epoch')
        if epoch:
            epoch_str = epoch.isoformat() if isinstance(epoch, datetime) else str(epoch)
            if epoch_str in merged_data:
                merged_data[epoch_str]['vx'] = row.get('vx')
                merged_data[epoch_str]['vy'] = row.get('vy')
                merged_data[epoch_str]['vz'] = row.get('vz')
            else:
                # If no matching position data, create entry with velocity only
                merged_data[epoch_str] = {
                    'epoch': epoch_str,
                    'x': None,
                    'y': None,
                    'z': None,
                    'vx': row.get('vx'),
                    'vy': row.get('vy'),
                    'vz': row.get('vz')
                }
    
    # Write to CSV
    with open(csv_path, 'w', newline='') as csvfile:
        fieldnames = ['epoch', 'x', 'y', 'z', 'vx', 'vy', 'vz']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        # Sort by epoch before writing
        for epoch in sorted(merged_data.keys()):
            writer.writerow(merged_data[epoch])
    
    return csv_path


def run_od_executable(csv_path: str) -> Dict[str, Any]:
    """
    Run the OD executable after CSV creation.
    
    Args:
        csv_path: Path to the created measurement.csv file
        
    Returns:
        Dictionary with execution status and output
    """
    # Get the directory containing the CSV (OD-Release folder)
    od_release_dir = os.path.dirname(csv_path)
    
    # Path to the executable
    exe_path = os.path.join(od_release_dir, "dist", "OD_V2.0.0.exe")
    
    if not os.path.exists(exe_path):
        error_msg = f"Executable not found at: {exe_path}"
        print(f"ERROR: {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "exe_path": exe_path,
            "tle_saved": False,
            "tle_path": None
        }
    
    print(f"\nRunning OD executable: {exe_path}")
    print(f"Working directory: {od_release_dir}")
    print("=" * 80)
    
    try:
        # Set up environment with UTF-8 encoding to handle Unicode characters
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        # Run the executable with real-time output streaming
        result = subprocess.run(
            [exe_path],
            cwd=od_release_dir,
            timeout=300,  # 5 minute timeout
            env=env,  # Pass environment with UTF-8 encoding
            encoding='utf-8',  # Explicitly set encoding
            errors='replace'  # Replace characters that can't be decoded
            # No capture_output - logs will stream in real-time to terminal
        )
        
        print("=" * 80)
        print(f"Executable completed with return code: {result.returncode}\n")
        
        # If execution was successful, try to find and save the TLE
        tle_saved = False
        tle_path = None
        if result.returncode == 0:
            try:
                # Search for any generated TLE files under the OD release directory (covers Outputs/, Outputs_Tests/, etc.)
                import glob
                tle_files = glob.glob(os.path.join(od_release_dir, "**", "*.tle"), recursive=True)
                
                if tle_files:
                    # Get latest TLE file by modification time
                    latest_tle = max(tle_files, key=os.path.getmtime)
                    tle_path = latest_tle
                    # Read the TLE file
                    with open(latest_tle, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        
                    if len(lines) >= 2:
                        # Parse satellite name from filename
                        sat_name = os.path.basename(latest_tle).replace('OD_TLE_', '').replace('.tle', '')
                        
                        # Prepare data for saving
                        tle_data_to_save = {
                            "name": sat_name,
                            "line1": lines[0].strip(),
                            "line2": lines[1].strip()
                        }
                        
                        # Save to database
                        if save_tle_data(tle_data_to_save):
                            print(f"Successfully captured and saved generated TLE from: {latest_tle}")
                            tle_saved = True
                        else:
                            print(f"Failed to save generated TLE from: {latest_tle}")
                    else:
                        print(f"Invalid TLE file format: {latest_tle}")
                else:
                    print(f"No TLE files found under: {od_release_dir}")
                    
            except Exception as e:
                print(f"Error processing generated TLE: {e}")
                tle_saved = False
                tle_path = None

        return {
            "success": result.returncode == 0,
            "return_code": result.returncode,
            "exe_path": exe_path,
            "output_mode": "real-time streaming",
            "tle_saved": tle_saved,
            "tle_path": tle_path
        }
        
    except subprocess.TimeoutExpired:
        error_msg = "Executable execution timed out (5 minutes)"
        print(f"ERROR: {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "exe_path": exe_path,
            "tle_saved": False,
            "tle_path": None
        }
    except Exception as e:
        error_msg = f"Error running executable: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "exe_path": exe_path,
            "tle_saved": False,
            "tle_path": None
        }


def fetch_od_data(start_time: str, end_time: str) -> Dict[str, Any]:
    """
    Fetch OD data (position and velocity) and export to CSV.
    After CSV creation, automatically runs the OD executable.
    
    Args:
        start_time: Start timestamp (ISO format)
        end_time: End timestamp (ISO format)
        
    Returns:
        Dictionary containing position data, velocity data, CSV path, record counts, and executable result
    """
    # Use table name constants from db module
    pos_data = fetch_data(Tables.POSITION, start_time, end_time)
    vel_data = fetch_data(Tables.VELOCITY, start_time, end_time)
    
    # Write data to CSV in the OD folder
    od_service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = write_measurements_csv(pos_data, vel_data, od_service_dir)
    
    print(f"CSV created successfully at: {csv_path}")
    
    # Run the OD executable after CSV creation
    exe_result = run_od_executable(csv_path)
    
    return {
        "position": pos_data,
        "velocity": vel_data,
        "csv_exported": csv_path,
        "record_count": {
            "position": len(pos_data),
            "velocity": len(vel_data)
        },
        "executable_result": exe_result
    }
