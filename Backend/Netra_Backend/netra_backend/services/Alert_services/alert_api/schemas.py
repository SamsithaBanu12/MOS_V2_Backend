from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AlertBase(BaseModel):
    timestamp: Optional[str] = None
    submodule_name: Optional[str] = None
    submodule_id: Optional[str] = None
    metric: Optional[str] = None
    value: Optional[float] = None
    min_limit: Optional[float] = None
    max_limit: Optional[float] = None
    severity: Optional[str] = None
    reason: Optional[str] = None
    packet_raw: Optional[str] = None
    packet_matched: Optional[str] = None
    status: Optional[str] = None

class AlertCreate(AlertBase):
    pass

class Alert(AlertBase):
    id: int
    engine_time: datetime

    class Config:
        from_attributes = True
