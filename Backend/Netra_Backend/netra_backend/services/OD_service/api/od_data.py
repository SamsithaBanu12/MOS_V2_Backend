"""
OD Data API endpoints.
Handles orbit determination data queries.
"""

import sys
import os
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.od_data_handler import fetch_od_data

router = APIRouter(prefix="/od", tags=["OD Data"])


@router.get("/data")
async def get_od_data(start_time: str, end_time: str) -> Dict[str, Any]:
    """
    Fetch Position and Velocity data within the specified timestamp range.
    Timestamps should be in ISO format (e.g., 2026-03-01T10:00:00).
    Uses 'epoch' column for filtering (actual measurement timestamp).
    
    Note: For automated daily exports, use the scheduler instead.
    """
    try:
        result = fetch_od_data(start_time, end_time)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching OD data: {str(e)}")
