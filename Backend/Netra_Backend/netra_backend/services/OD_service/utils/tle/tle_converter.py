"""
TLE (Two-Line Element) to WGS84 converter for satellite tracking.
Converts TLE data to latitude, longitude, altitude coordinates.
And fetches TLE data directly from the database.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sgp4.api import Satrec, jday
import numpy as np

# Add parent directory to path to import od_data_handler
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from od_data_handler import fetch_latest_tle


def tle_to_wgs84(line1: str, line2: str, time_points: int = 100, duration_hours: float = 24.0) -> List[Dict[str, Any]]:
    """
    Convert TLE to WGS84 coordinates over a time period.
    
    Args:
        line1: TLE line 1
        line2: TLE line 2
        time_points: Number of position points to generate
        duration_hours: Duration in hours to propagate
        
    Returns:
        List of dictionaries with timestamp, lat, lon, alt
    """
    try:
        # Create satellite object from TLE
        satellite = Satrec.twoline2rv(line1, line2)
        
        # Generate time points
        start_time = datetime.utcnow()
        positions = []
        
        for i in range(time_points):
            # Calculate time for this point
            dt = start_time + timedelta(hours=(duration_hours * i / time_points))
            
            # Convert to Julian date
            jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
            
            # Propagate satellite position
            e, r, v = satellite.sgp4(jd, fr)
            
            if e != 0:  # Error in propagation
                continue
            
            # Convert TEME coordinates (r) to WGS84
            # r is in km, need to convert to lat/lon/alt
            x, y, z = r  # Position in km
            
            # Calculate latitude, longitude, altitude
            # Altitude (distance from Earth center minus Earth radius)
            alt_km = np.sqrt(x**2 + y**2 + z**2) - 6371.0  # Earth radius ~6371 km
            
            # Latitude (in degrees)
            lat = np.degrees(np.arcsin(z / np.sqrt(x**2 + y**2 + z**2)))
            
            # Longitude (in degrees)
            lon = np.degrees(np.arctan2(y, x))
            
            positions.append({
                "timestamp": dt.isoformat() + "Z",
                "latitude": float(lat),
                "longitude": float(lon),
                "altitude_km": float(alt_km),
                "velocity_km_s": {
                    "x": float(v[0]),
                    "y": float(v[1]),
                    "z": float(v[2])
                }
            })
        
        return positions
    
    except Exception as e:
        print(f"Error converting TLE to WGS84: {e}")
        return []


def get_satellite_track(tle_path: Optional[str] = None, time_points: int = 100, duration_hours: float = 24.0) -> Dict[str, Any]:
    """
    Get satellite tracking data using TLE from the database.
    
    Args:
        tle_path: IGNORED (kept for backward compatibility only)
        time_points: Number of position points
        duration_hours: Duration to propagate
        
    Returns:
        Dictionary with satellite tracking data
    """
    # Fetch latest TLE from database
    tle_data = fetch_latest_tle()
    
    if tle_data is None:
        return {
            "success": False,
            "error": "No TLE data found in database"
        }
    
    # Convert to WGS84
    positions = tle_to_wgs84(tle_data["line1"], tle_data["line2"], time_points, duration_hours)
    
    if not positions:
        return {
            "success": False,
            "error": "Failed to generate satellite positions from TLE"
        }
    
    return {
        "success": True,
        "satellite_name": tle_data["name"],
        "source": "database",
        "created_at": str(tle_data.get("created_at")),
        "time_points": len(positions),
        "duration_hours": duration_hours,
        "positions": positions,
        "metadata": {
            "line1": tle_data["line1"],
            "line2": tle_data["line2"],
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
    }
