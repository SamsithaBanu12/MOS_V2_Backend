"""
TLE (Two-Line Element) to WGS84 converter for satellite tracking.
Converts TLE data to latitude, longitude, altitude coordinates.
And fetches TLE data directly from the database.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from skyfield.api import load, EarthSatellite, wgs84

# Add parent directory to path to import od_data_handler
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from od_data_handler import fetch_latest_tle


def tle_to_wgs84(line1: str, line2: str, time_points: int = 100, duration_hours: float = 24.0, past_hours: float = 0.0) -> List[Dict[str, Any]]:
    """
    Convert TLE to WGS84 coordinates over a time period, accounting for Earth's rotation.
    
    Args:
        line1: TLE line 1
        line2: TLE line 2
        time_points: Number of position points to generate
        duration_hours: Duration in hours to propagate into the future
        past_hours: Duration in hours to propagate into the past
        
    Returns:
        List of dictionaries with timestamp, lat, lon, alt and velocity
    """
    try:
        # Initialize timescale (use builtin to avoid downloading leap second files from the internet)
        ts = load.timescale(builtin=True)
        
        # Create satellite object from TLE
        satellite = EarthSatellite(line1, line2, "Satellite", ts)
        
        # Generate time points starting from (now - past_hours)
        current_time = datetime.now(timezone.utc)
        start_time = current_time - timedelta(hours=past_hours)
        total_duration = duration_hours + past_hours
        
        positions = []
        
        for i in range(time_points):
            # Calculate time for this point
            # Avoid division by zero if time_points is 1
            if time_points > 1:
                progress = i / (time_points - 1)
            else:
                progress = 0
            
            dt = start_time + timedelta(hours=(total_duration * progress))
            t = ts.from_datetime(dt)
            
            # Propagate satellite position (TEME frame)
            geocentric = satellite.at(t)
            
            # Convert to sub-satellite point (Latitude, Longitude, Altitude)
            # This transformation accounts for Earth's rotation (ECEF/WGS84)
            subpoint = wgs84.subpoint(geocentric)
            
            # Get velocity in km/s (TEME frame)
            v = geocentric.velocity.km_per_s
            
            positions.append({
                "timestamp": dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                "latitude": float(subpoint.latitude.degrees),
                "longitude": float(subpoint.longitude.degrees),
                "altitude_km": float(subpoint.elevation.km),
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


def get_satellite_track(tle_path: Optional[str] = None, time_points: int = 100, duration_hours: float = 24.0, past_hours: float = 0.0) -> Dict[str, Any]:
    """
    Get satellite tracking data using TLE from the database.
    
    Args:
        tle_path: IGNORED (kept for backward compatibility only)
        time_points: Number of position points
        duration_hours: Duration to propagate
        past_hours: Duration to propagate into the past
        
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
    positions = tle_to_wgs84(tle_data["line1"], tle_data["line2"], time_points, duration_hours, past_hours)
    
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
