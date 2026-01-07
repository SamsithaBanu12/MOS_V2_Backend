from typing import Dict, List, Optional
from pydantic import BaseModel

# -------------------------------
# Stations
# -------------------------------
class StationOut(BaseModel):
    id: str
    name: str
    broker_b_host: str
    broker_b_port: int
    broker_b_username: Optional[str] = ""
    topic_uplink: str
    topic_downlink: str

    # Health (per-station)
    health_host: Optional[str] = None
    health_port: Optional[int] = None
    health_sband_topic: Optional[str] = None
    health_xband_topic: Optional[str] = None


# -------------------------------
# Status / Counters
# -------------------------------
class CountersTopic(BaseModel):
    rx_msgs: int
    rx_bytes: int
    tx_msgs: int
    tx_bytes: int

class StatusOut(BaseModel):
    a_connected: bool
    b_connected: bool
    # topic -> counters (flat), e.g. "cosmos/command": {rx_msgs, rx_bytes, tx_msgs, tx_bytes}
    counters: Dict[str, CountersTopic]
    # keep whatever you put in config (e.g., {"station": "gs-a"})
    config: Dict


# -------------------------------
# Bridge topic messages (/messages)
# -------------------------------
class MessageRow(BaseModel):
    id: int
    ts_utc: str
    direction: Optional[str] = None
    bytes: int
    display_text: Optional[str] = None
    # mqtt_topic optional if you want it later
    # mqtt_topic: Optional[str] = None


# -------------------------------
# Health streams (/health/messages)
# -------------------------------
class HealthMsg(BaseModel):
    id: int
    ts_utc: str
    bytes: int
    display_text: Optional[str] = None
    mqtt_topic: Optional[str] = None

class HealthList(BaseModel):
    items: List[HealthMsg]
    total: Optional[int] = None
