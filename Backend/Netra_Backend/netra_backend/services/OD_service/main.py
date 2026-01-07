"""
OD Service FastAPI Server
Minimal API for OD data access and satellite tracking.
Main data export functionality has been moved to scheduled jobs.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import od_data_router, satellite_router

app = FastAPI(
    title="OD Service",
    description="API to fetch ADCS Position/Velocity Data and Satellite Tracking",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(od_data_router)
app.include_router(satellite_router)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "service": "OD Service",
        "version": "1.0.0",
        "endpoints": {
            "od_data": "/od/data",
            "satellite_track": "/satellite/track",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "OD Service"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8030, reload=True)
