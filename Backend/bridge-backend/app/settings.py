import os
from pathlib import Path

# ---------- Paths ----------
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = str(BASE_DIR / "bridge.sqlite3")
SQLITE_URL = f"sqlite:///{DB_PATH}"

# ---------- Broker A (MCS) constants — fixed ----------
BROKER_A_HOST_DEF = os.getenv("BROKER_A_HOST", "localhost")
BROKER_A_PORT_DEF = int(os.getenv("BROKER_A_PORT", "2147"))

# ---------- CORS ----------
ALLOWED_CORS = ["http://localhost:5173", "http://127.0.0.1:5173", "*"]

# ---------- Logical topics (A side fixed; B side per-station) ----------
TOPIC_COSMOS_COMMAND   = "cosmos/command"
TOPIC_COSMOS_TELEMETRY = "cosmos/telemetry"

# ---------- Stations config path ----------
STATIONS_FILE = BASE_DIR / "stations.json"

