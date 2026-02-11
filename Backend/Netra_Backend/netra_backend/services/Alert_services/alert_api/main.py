from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

import models
import schemas
from database import get_db

app = FastAPI(title="Alert Service API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/alerts", response_model=List[schemas.Alert])
async def get_alerts(db: AsyncSession = Depends(get_db)):
    """
    Fetch all alerts from the database.
    """
    try:
        result = await db.execute(select(models.Alert))
        alerts = result.scalars().all()
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alerts/{alert_id}", response_model=schemas.Alert)
async def get_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """
    Fetch a single alert by ID.
    """
    result = await db.execute(select(models.Alert).where(models.Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@app.patch("/alerts/{alert_id}/status", response_model=schemas.Alert)
async def update_alert_status(alert_id: int, update_data: schemas.AlertUpdateStatus, db: AsyncSession = Depends(get_db)):
    """
    Update the status of an alert.
    Allowed statuses: alert_identified, acknowledged, resolved, dismissed
    """
    # Validate status against Enum
    valid_statuses = [s.value for s in schemas.AlertStatus]
    if update_data.status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Incorrect option. Allowed values are: {', '.join(valid_statuses)}"
        )

    # Fetch the alert
    result = await db.execute(select(models.Alert).where(models.Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Update status
    alert.status = update_data.status
    await db.commit()
    await db.refresh(alert)
    
    return alert

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
