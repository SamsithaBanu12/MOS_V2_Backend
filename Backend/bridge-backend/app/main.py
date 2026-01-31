import asyncio, json, sqlite3
from typing import List, Dict, Optional

from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, Query, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func  # 👈 needed for DB totals

from .db import Base, engine, get_db, DB_PATH
from .models import (
    CosmosCommandLog, CosmosTelemetryLog, SatosUplinkLog, SatosDownlinkLog,
    TOPIC_TO_MODEL, HEALTH_SBAND_LOG, HEALTH_XBAND_LOG,
)
from .schemas import StationOut, StatusOut, MessageRow, HealthList, HealthMsg
from .settings import (
    ALLOWED_CORS, BROKER_A_HOST_DEF, BROKER_A_PORT_DEF, STATIONS_FILE
)
from .stats import Stats
from .mqtt_bridge import BridgeRunner, HealthRunner

# Logical topics (stable keys used across API/UI)
LOGICAL_TOPICS = (
    "cosmos/command",
    "cosmos/telemetry",
    "SatOS/uplink",
    "SatOS/downlink",
)

# ---------- Security (RBAC) ----------
def verify_role(allowed_roles: List[str]):
    async def role_checker(x_user_roles: str = Header(None, alias="X-User-Roles")):
        if not x_user_roles:
            raise HTTPException(status_code=401, detail="Gateway authentication required")
        if x_user_roles not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"Permission denied: {x_user_roles} role cannot perform this action")
        return x_user_roles
    return role_checker

CONNECTION_ROLES = ["SUPER_ADMIN", "ADMIN", "MISSION_OPERATOR"]

async def gateway_auth_only(x_user_id: str = Header(None, alias="X-User-Id")):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Internal Gateway Authentication Required")
    return x_user_id

# ---------- app & cors ----------
app = FastAPI(
    title="Bridge Backend", 
    version="2.3",
    dependencies=[Depends(gateway_auth_only)]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_CORS, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ---------- DB setup ----------
Base.metadata.create_all(bind=engine)

# lightweight migrations for new columns / indices
def _ensure_columns():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    def missing(table, col):
        cur.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in cur.fetchall()]
        return col not in cols
    # main 4 logs: ensure station_id/mqtt_topic
    for tbl in ["COSMOS_COMMAND_LOG","COSMOS_TELEMETRY_LOG","SATOS_UPLINK_LOG","SATOS_DOWNLINK_LOG"]:
        if missing(tbl, "station_id"):
            cur.execute(f"ALTER TABLE {tbl} ADD COLUMN station_id TEXT NOT NULL DEFAULT 'default'")
        if missing(tbl, "mqtt_topic"):
            cur.execute(f"ALTER TABLE {tbl} ADD COLUMN mqtt_topic TEXT")
    # health logs: ensure station_id/mqtt_topic
    for tbl in ["HEALTH_SBAND_LOG","HEALTH_XBAND_LOG"]:
        if missing(tbl, "station_id"):
            cur.execute(f"ALTER TABLE {tbl} ADD COLUMN station_id TEXT NOT NULL DEFAULT 'default'")
        if missing(tbl, "mqtt_topic"):
            cur.execute(f"ALTER TABLE {tbl} ADD COLUMN mqtt_topic TEXT")
    # indices
    cur.execute("CREATE INDEX IF NOT EXISTS ix_cmd_station_ts ON COSMOS_COMMAND_LOG(station_id, id)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_tlm_station_ts ON COSMOS_TELEMETRY_LOG(station_id, id)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_up_station_ts  ON SATOS_UPLINK_LOG(station_id, id)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_dn_station_ts  ON SATOS_DOWNLINK_LOG(station_id, id)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_hs_station_ts  ON HEALTH_SBAND_LOG(station_id, id)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_hx_station_ts  ON HEALTH_XBAND_LOG(station_id, id)")
    con.commit(); con.close()
_ensure_columns()

# ---------- stations ----------
with open(STATIONS_FILE, "r", encoding="utf-8") as f:
    _raw_stations = json.load(f)

# Patch localhost -> host.docker.internal if running in Docker
import os
if os.getenv("RUNNING_IN_DOCKER") == "true":
    for s in _raw_stations:
        for k in ["broker_b_host", "health_host"]:
            if s.get(k) == "localhost":
                s[k] = "host.docker.internal"

STATIONS = { s["id"]: s for s in _raw_stations }

def station_or_404(station_id: str) -> Dict:
    st = STATIONS.get(station_id)
    if not st:
        raise HTTPException(status_code=404, detail=f"Unknown station '{station_id}'")
    return st


# ---------- globals ----------
stats = Stats()
ws_clients: List[WebSocket] = []
event_loop: asyncio.AbstractEventLoop | None = None

# broadcast helpers
async def broadcast(msg: Dict):
    dead = []
    for ws in ws_clients:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.append(ws)
    for d in dead:
        if d in ws_clients:
            ws_clients.remove(d)

def threadsafe_push(msg: Dict):
    if event_loop and event_loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast(msg), event_loop)

@app.on_event("startup")
async def _on_startup():
    global event_loop
    event_loop = asyncio.get_running_loop()

# ---- Bridge + Health Manager (per-station) ----
class BridgeManager:
    def __init__(self):
        self.runners: Dict[str, BridgeRunner] = {}     # station_id -> bridge
        self.health:  Dict[str, HealthRunner]  = {}    # station_id -> health

    def connect(self, station_id: str):
        st = station_or_404(station_id)

        # BridgeRunner
        if station_id not in self.runners or not (self.runners[station_id]._thread and self.runners[station_id]._thread.is_alive()):
            def on_status(which: str, ok: bool, sid: str):
                threadsafe_push({"type":"status", "station": sid, "which": which, "ok": ok})

            def on_event(evt: Dict, sid: str):
                threadsafe_push({**evt, "station": sid})

            br = BridgeRunner(
                station_id=station_id,
                b_host=st["broker_b_host"], b_port=st["broker_b_port"],
                b_user=st.get("broker_b_username",""), b_pass=st.get("broker_b_password",""),
                topic_uplink=st["topic_uplink"], topic_downlink=st["topic_downlink"],
                stats=stats, on_status=on_status, on_event=on_event
            )
            self.runners[station_id] = br
            br.connect(BROKER_A_HOST_DEF, BROKER_A_PORT_DEF, db_factory=lambda: next(get_db()))

        # HealthRunner (per station) – start alongside the bridge
        self.ensure_health(station_id)

    def ensure_health(self, station_id: str):
        """Start only the health runner for a station (no-op if already running)."""
        st = station_or_404(station_id)
        if station_id in self.health and self.health[station_id].thread and self.health[station_id].thread.is_alive():
            return
        hr = HealthRunner(
            station_id=station_id,
            host=st.get("health_host", "localhost"),
            port=int(st.get("health_port", 2147)),
            sband_topic=st.get("health_sband_topic", "sband/health"),
            xband_topic=st.get("health_xband_topic", "xband/health"),
            db_factory=lambda: next(get_db()),
            ws_nudge=threadsafe_push,
        )
        self.health[station_id] = hr
        hr.start()

    def disconnect(self, station_id: str):
        if station_id in self.runners:
            self.runners[station_id].disconnect()
        if station_id in self.health:
            self.health[station_id].stop()

    def status(self, station_id: str):
        r = self.runners.get(station_id)
        a_ok = bool(r and r.a_connected)
        b_ok = bool(r and r.b_connected)
        return a_ok, b_ok


BRIDGES = BridgeManager()

# ---------- DB totals helper for /status ----------
def _db_totals_for_station(db: Session, station_id: str) -> Dict[str, Dict[str, int]]:
    """
    Build totals for each logical topic from the DB, matching our direction semantics:
      - cosmos/command:   RX from A (AtoB)
      - SatOS/uplink:     TX to B  (AtoB)
      - SatOS/downlink:   RX from B (BtoA)
      - cosmos/telemetry: TX to A  (BtoA)
    """
    totals = {
        "cosmos/command":   {"rx_msgs": 0, "rx_bytes": 0, "tx_msgs": 0, "tx_bytes": 0},
        "cosmos/telemetry": {"rx_msgs": 0, "rx_bytes": 0, "tx_msgs": 0, "tx_bytes": 0},
        "SatOS/uplink":     {"rx_msgs": 0, "rx_bytes": 0, "tx_msgs": 0, "tx_bytes": 0},
        "SatOS/downlink":   {"rx_msgs": 0, "rx_bytes": 0, "tx_msgs": 0, "tx_bytes": 0},
    }

    # cosmos/command -> RX from A (AtoB)
    c, b = (db.query(func.count(CosmosCommandLog.id), func.coalesce(func.sum(CosmosCommandLog.bytes), 0))
              .filter(CosmosCommandLog.station_id == station_id,
                      CosmosCommandLog.direction == "AtoB")).one()
    totals["cosmos/command"]["rx_msgs"]  = int(c or 0)
    totals["cosmos/command"]["rx_bytes"] = int(b or 0)

    # SatOS/uplink -> TX to B (AtoB)
    c, b = (db.query(func.count(SatosUplinkLog.id), func.coalesce(func.sum(SatosUplinkLog.bytes), 0))
              .filter(SatosUplinkLog.station_id == station_id,
                      SatosUplinkLog.direction == "AtoB")).one()
    totals["SatOS/uplink"]["tx_msgs"]  = int(c or 0)
    totals["SatOS/uplink"]["tx_bytes"] = int(b or 0)

    # SatOS/downlink -> RX from B (BtoA)
    c, b = (db.query(func.count(SatosDownlinkLog.id), func.coalesce(func.sum(SatosDownlinkLog.bytes), 0))
              .filter(SatosDownlinkLog.station_id == station_id,
                      SatosDownlinkLog.direction == "BtoA")).one()
    totals["SatOS/downlink"]["rx_msgs"]  = int(c or 0)
    totals["SatOS/downlink"]["rx_bytes"] = int(b or 0)

    # cosmos/telemetry -> TX to A (BtoA)
    c, b = (db.query(func.count(CosmosTelemetryLog.id), func.coalesce(func.sum(CosmosTelemetryLog.bytes), 0))
              .filter(CosmosTelemetryLog.station_id == station_id,
                      CosmosTelemetryLog.direction == "BtoA")).one()
    totals["cosmos/telemetry"]["tx_msgs"]  = int(c or 0)
    totals["cosmos/telemetry"]["tx_bytes"] = int(b or 0)

    return totals

# ---------- endpoints ----------

@app.get("/stations", response_model=List[StationOut])
def get_stations():
    out = []
    for s in STATIONS.values():
        out.append({
            "id": s["id"], "name": s["name"],
            "broker_b_host": s["broker_b_host"], "broker_b_port": s["broker_b_port"],
            "broker_b_username": s.get("broker_b_username",""),
            "topic_uplink": s["topic_uplink"], "topic_downlink": s["topic_downlink"],
            "health_host": s.get("health_host","localhost"),
            "health_port": s.get("health_port",2147),
            "health_sband_topic": s.get("health_sband_topic","sband/health"),
            "health_xband_topic": s.get("health_xband_topic","xband/health")
        })
    return out

@app.post("/connect", dependencies=[Depends(verify_role(CONNECTION_ROLES))])
def connect(station: str = Query(...)):
    station_or_404(station)
    BRIDGES.connect(station)
    return {"ok": True}

@app.post("/disconnect", dependencies=[Depends(verify_role(CONNECTION_ROLES))])
def disconnect(station: str = Query(...)):
    station_or_404(station)
    BRIDGES.disconnect(station)
    return {"ok": True}

@app.get("/status", response_model=StatusOut)
def status(station: str = Query(...), db: Session = Depends(get_db)):
    station_or_404(station)
    a_ok, b_ok = BRIDGES.status(station)

    # live (in-memory) counters
    live = stats.snapshot(station)  # {topic: {rx_msgs,rx_bytes,tx_msgs,tx_bytes}}
    for t in LOGICAL_TOPICS:
        live.setdefault(t, {"rx_msgs":0,"rx_bytes":0,"tx_msgs":0,"tx_bytes":0})

    # DB totals as fallback
    db_tot = _db_totals_for_station(db, station)

    merged = {}
    for t in LOGICAL_TOPICS:
        lv = live[t]
        if lv["rx_msgs"] == 0 and lv["rx_bytes"] == 0 and lv["tx_msgs"] == 0 and lv["tx_bytes"] == 0:
            merged[t] = db_tot[t]   # show DB totals if live is empty (e.g., after restart)
        else:
            merged[t] = lv          # prefer live when present

    return {
        "a_connected": a_ok,
        "b_connected": b_ok,
        "counters": merged,
        "config": {"station": station}
    }

@app.get("/messages", response_model=List[MessageRow])
def get_messages(
    station: str = Query(...),
    topic: str = Query(..., regex="^(cosmos/command|cosmos/telemetry|SatOS/uplink|SatOS/downlink)$"),
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    station_or_404(station)
    Model = TOPIC_TO_MODEL[topic]
    rows = (db.query(Model)
              .filter(Model.station_id == station)
              .order_by(Model.id.desc())
              .offset(offset).limit(limit).all())
    return [
        MessageRow(id=r.id, ts_utc=r.ts_utc, direction=r.direction, bytes=r.bytes, display_text=r.display_text)
        for r in rows
    ]

@app.get("/health/messages", response_model=HealthList)
def get_health_messages(
    station: str = Query(...),
    band: str = Query(..., regex="^(sband|xband)$"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    station_or_404(station)
    # ensure health subscriptions even if /connect wasn't called
    BRIDGES.ensure_health(station)

    Model = HEALTH_SBAND_LOG if band == "sband" else HEALTH_XBAND_LOG
    rows = (db.query(Model)
              .filter(Model.station_id == station)
              .order_by(Model.id.desc())
              .offset(offset).limit(limit).all())
    items = [
        HealthMsg(
            id=r.id, ts_utc=r.ts_utc, bytes=r.bytes,
            display_text=r.display_text, mqtt_topic=r.mqtt_topic
        ) for r in rows
    ]
    return {"items": items}

@app.get("/stats")
def get_stats(station: Optional[str] = None):
    if station:
        station_or_404(station)
        return stats.snapshot(station)
    return stats.snapshot()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.append(ws)
    try:
        while True:
            await ws.receive_text()  # keepalive
    except WebSocketDisconnect:
        pass
    finally:
        if ws in ws_clients:
            ws_clients.remove(ws)
