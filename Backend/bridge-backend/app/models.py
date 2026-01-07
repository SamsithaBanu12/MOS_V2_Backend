from sqlalchemy import Column, Integer, String, LargeBinary, Text, Index
from .db import Base

# ─────────────────────────────────────────────────────────────
# Bridge logs (existing 4 tables)
# ─────────────────────────────────────────────────────────────

class CosmosCommandLog(Base):
  __tablename__ = "COSMOS_COMMAND_LOG"
  id = Column(Integer, primary_key=True, index=True)
  ts_utc = Column(String, index=True)
  direction = Column(String)   # AtoB | BtoA
  bytes = Column(Integer)
  raw_blob = Column(LargeBinary)
  display_text = Column(Text)
  meta_json = Column(Text)

  station_id = Column(String, index=True, nullable=False, default="default")
  mqtt_topic = Column(String, nullable=True)
  __table_args__ = (Index("ix_cmd_station_ts", "station_id", "id"),)


class CosmosTelemetryLog(Base):
  __tablename__ = "COSMOS_TELEMETRY_LOG"
  id = Column(Integer, primary_key=True, index=True)
  ts_utc = Column(String, index=True)
  direction = Column(String)
  bytes = Column(Integer)
  raw_blob = Column(LargeBinary)
  display_text = Column(Text)
  meta_json = Column(Text)

  station_id = Column(String, index=True, nullable=False, default="default")
  mqtt_topic = Column(String, nullable=True)
  __table_args__ = (Index("ix_tlm_station_ts", "station_id", "id"),)


class SatosUplinkLog(Base):
  __tablename__ = "SATOS_UPLINK_LOG"
  id = Column(Integer, primary_key=True, index=True)
  ts_utc = Column(String, index=True)
  direction = Column(String)
  bytes = Column(Integer)
  raw_blob = Column(LargeBinary)
  display_text = Column(Text)
  meta_json = Column(Text)

  station_id = Column(String, index=True, nullable=False, default="default")
  mqtt_topic = Column(String, nullable=True)
  __table_args__ = (Index("ix_up_station_ts", "station_id", "id"),)


class SatosDownlinkLog(Base):
  __tablename__ = "SATOS_DOWNLINK_LOG"
  id = Column(Integer, primary_key=True, index=True)
  ts_utc = Column(String, index=True)
  direction = Column(String)
  bytes = Column(Integer)
  raw_blob = Column(LargeBinary)
  display_text = Column(Text)
  meta_json = Column(Text)

  station_id = Column(String, index=True, nullable=False, default="default")
  mqtt_topic = Column(String, nullable=True)
  __table_args__ = (Index("ix_dn_station_ts", "station_id", "id"),)


# Logical topic -> Model mapping for /messages
TOPIC_TO_MODEL = {
  "cosmos/command":   CosmosCommandLog,
  "cosmos/telemetry": CosmosTelemetryLog,
  "SatOS/uplink":     SatosUplinkLog,
  "SatOS/downlink":   SatosDownlinkLog,
}

# ─────────────────────────────────────────────────────────────
# NEW: Health logs (per-station)
# ─────────────────────────────────────────────────────────────

class HealthSbandLog(Base):
  __tablename__ = "HEALTH_SBAND_LOG"
  id = Column(Integer, primary_key=True, index=True)
  ts_utc = Column(String, index=True)
  bytes = Column(Integer)
  raw_blob = Column(LargeBinary)
  display_text = Column(Text)          # decoded text (usually JSON/text)
  meta_json = Column(Text, nullable=True)

  station_id = Column(String, index=True, nullable=False, default="default")
  mqtt_topic = Column(String, nullable=True)

  __table_args__ = (Index("ix_hs_station_ts", "station_id", "id"),)


class HealthXbandLog(Base):
  __tablename__ = "HEALTH_XBAND_LOG"
  id = Column(Integer, primary_key=True, index=True)
  ts_utc = Column(String, index=True)
  bytes = Column(Integer)
  raw_blob = Column(LargeBinary)
  display_text = Column(Text)
  meta_json = Column(Text, nullable=True)

  station_id = Column(String, index=True, nullable=False, default="default")
  mqtt_topic = Column(String, nullable=True)

  __table_args__ = (Index("ix_hx_station_ts", "station_id", "id"),)


# Convenience aliases to match imports used in main.py
HEALTH_SBAND_LOG = HealthSbandLog
HEALTH_XBAND_LOG = HealthXbandLog
