"""
API routes for OD Service.
"""

from .od_data import router as od_data_router
from .satellite import router as satellite_router

__all__ = ["od_data_router", "satellite_router"]
