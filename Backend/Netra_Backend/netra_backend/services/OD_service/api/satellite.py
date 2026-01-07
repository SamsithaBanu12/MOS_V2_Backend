"""
Satellite Tracking API endpoints.
Handles TLE to WGS84 conversion for satellite tracking.
"""

import sys
import os
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.tle.tle_converter import get_satellite_track

router = APIRouter(prefix="/satellite", tags=["Satellite Tracking"])


@router.get("/track")
async def get_satellite_track_data(
    tle_file: Optional[str] = Query(None, description="Path to specific TLE file (optional, uses latest if not provided)"),
    time_points: int = Query(100, ge=10, le=1000, description="Number of position points to generate"),
    duration_hours: float = Query(24.0, ge=0.1, le=168.0, description="Propagation duration in hours (max 1 week)")
) -> Dict[str, Any]:
    """
    Get satellite tracking data from TLE file converted to WGS84 coordinates.
    
    Parameters:
    - tle_file: Optional path to TLE file (defaults to latest TLE)
    - time_points: Number of position points (10-1000, default 100)
    - duration_hours: Duration in hours (1-168, default 24)
    
    Returns:
    - Satellite positions in WGS84 (lat, lon, alt)
    - Velocity vectors
    - TLE metadata
    """
    try:
        result = get_satellite_track(
            tle_path=tle_file,
            time_points=time_points,
            duration_hours=duration_hours
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "Failed to generate satellite track")
            )
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating satellite track: {str(e)}")
