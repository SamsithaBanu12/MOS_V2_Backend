from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, Text, func
from database import Base

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String(255))
    engine_time = Column(TIMESTAMP, server_default=func.now())
    submodule_name = Column(String(255))
    submodule_id = Column(String(255))
    metric = Column(String(255))
    value = Column(Float)
    min_limit = Column(Float)
    max_limit = Column(Float)
    severity = Column(String(50))
    reason = Column(Text)
    packet_raw = Column(String(255))
    packet_matched = Column(String(255))
    status = Column(String(50), server_default="alert_identified")
