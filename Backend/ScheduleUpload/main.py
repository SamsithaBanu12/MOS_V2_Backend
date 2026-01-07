# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timezone
import json
import subprocess
import os
import sys
import uuid
import time

import requests  # used to talk to OpenC3

BASE_DIR = Path(__file__).resolve().parent
SCHEDULES_DIR = BASE_DIR / "schedules"
GENERATED_DIR = BASE_DIR / "generated_schedules"
GENERATED_DIR.mkdir(exist_ok=True, parents=True)

# OpenC3 config (same as in schedular_script.py)
OPEN_C3_URL = os.getenv("OPEN_C3_URL", "http://host.docker.internal:2900/openc3-api/api")
OPEN_C3_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "mos12345",
}

# --- Load telemetry mapping ---
TELEM_MAPPING_FILE = BASE_DIR / "telemetry_mapping.json"
try:
    with TELEM_MAPPING_FILE.open("r", encoding="utf-8") as f:
        TELEMETRY_MAPPING: Dict[str, str] = json.load(f)
except Exception:
    TELEMETRY_MAPPING = {}

# --- In-memory run tracking ---
# RUNS[run_id] = {
#   "created_at": float,
#   "schedule_file": str,
#   "commands": [
#       {
#           "index": int,
#           "commandName": str,
#           "lookUpTable": str,
#           "scheduledTimestamp": float,
#           "delay": int,
#           "receivedTimestamp": Optional[float],
#           "status": "SCHEDULED" | "EXECUTED" | "FAILED",
#           "telemetry": Optional[dict],
#           "tm_name": Optional[str],
#       },
#       ...
#   ]
# }
RUNS: Dict[str, Dict[str, Any]] = {}

# --- FastAPI setup ---
app = FastAPI(title="Satellite Schedule Tester API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------- MODELS ---------
class ScheduleInfo(BaseModel):
    id: str
    filename: str
    label: str


class ScheduleGenerateRequest(BaseModel):
    schedule_name: str          # filename in schedules/ dir
    start_time_utc: str         # ISO string
    delays: List[int]           # one per command


class ScheduleEntry(BaseModel):
    subsystemName: str
    commandName: str
    LookUpTableID: str
    Timestamp: str
    SrcID: str
    DestID: str
    TCID: str
    RadioID: str
    Offset: str
    Length: str
    Payload: Optional[str] = ""
    Delay: Optional[int] = 0    # for UI only


class ScheduleGenerateResponse(BaseModel):
    generated_filename: str
    entries: List[ScheduleEntry]


class UploadRequest(BaseModel):
    generated_filename: str     # filename in generated_schedules/


class CommandStatus(BaseModel):
    index: int
    commandName: str
    lookUpTable: str
    scheduledTimestamp: float
    delay: int
    receivedTimestamp: Optional[float] = None
    status: str
    telemetry: Optional[Dict[str, Any]] = None


class UploadResponse(BaseModel):
    success: bool
    message: str
    log_path: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    run_id: Optional[str] = None
    commands: Optional[List[CommandStatus]] = None


class RunStatusResponse(BaseModel):
    run_id: str
    all_done: bool
    commands: List[CommandStatus]


# --------- HELPERS ---------
def parse_start_time_to_epoch(start_time_utc: str) -> int:
    """
    Parse an ISO string into an epoch (UTC).
    Accepts "YYYY-MM-DDTHH:MM:SSZ" or "YYYY-MM-DDTHH:MM:SS+00:00".
    If no tz is provided, assume UTC.
    """
    try:
        s = start_time_utc.strip()
        if s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid start_time_utc: {e}")


def load_schedule_file(path: Path) -> List[dict]:
    if not path.exists():
        raise HTTPException(status_code=404, detail="Schedule file not found")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="Schedule JSON must be an array")
    return data


def now_epoch() -> float:
    return time.time()


def poll_tm_packet(tm_name: str) -> Optional[Dict[str, Any]]:
    """
    Call OpenC3 get_tlm_packet for a given telemetry packet name.
    Returns a dict of fields (e.g. {"TIMESTAMP": ..., "RECEIVED_TIMESECONDS": ...})
    or None if no/invalid response.
    """
    payload = {
        "jsonrpc": "2.0",
        "method": "get_tlm_packet",
        "params": ["EMULATOR", tm_name],
        "id": 9,
        "keyword_params": {"scope": "DEFAULT"},
    }
    try:
        resp = requests.post(
            OPEN_C3_URL, headers=OPEN_C3_HEADERS, json=payload, timeout=3
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None

    result = data.get("result")
    if not result or not isinstance(result, list):
        return None

    fields: Dict[str, Any] = {}
    for item in result:
        if isinstance(item, list) and len(item) >= 2:
            key = item[0]
            val = item[1]
            fields[key] = val
    return fields


# --------- ROUTES ---------
@app.get("/api/schedules", response_model=List[ScheduleInfo])
def list_schedules():
    """
    List available sample schedule files from schedules/ directory.
    """
    if not SCHEDULES_DIR.exists():
        return []
    items: List[ScheduleInfo] = []
    for f in sorted(SCHEDULES_DIR.glob("*.json")):
        items.append(
            ScheduleInfo(
                id=f.stem,
                filename=f.name,
                label=f.stem.replace("_", " ").title(),
            )
        )
    return items


@app.get("/api/schedules/{filename}")
def get_schedule(filename: str):
    """
    Return raw schedule entries for a given sample file (for preview/edit).
    """
    file_path = SCHEDULES_DIR / filename
    entries = load_schedule_file(file_path)
    return {"entries": entries}


@app.post("/api/schedules/generate", response_model=ScheduleGenerateResponse)
def generate_schedule(req: ScheduleGenerateRequest):
    """
    Take a base schedule + starting UTC time + per-command delays,
    compute new epoch timestamps, add Delay fields, and save a generated file.
    """
    base_path = SCHEDULES_DIR / req.schedule_name
    entries = load_schedule_file(base_path)

    if len(entries) != len(req.delays):
        raise HTTPException(
            status_code=400,
            detail=f"delays length ({len(req.delays)}) must equal number of commands ({len(entries)})",
        )

    start_epoch = parse_start_time_to_epoch(req.start_time_utc)

    # Compute timestamps sequentially
    current_ts = start_epoch
    new_entries: List[dict] = []

    for idx, (entry, delay) in enumerate(zip(entries, req.delays)):
        e = dict(entry)  # shallow copy
        if idx == 0:
            e["Timestamp"] = str(current_ts)
            e["Delay"] = 0
        else:
            current_ts += int(delay)
            e["Timestamp"] = str(current_ts)
            e["Delay"] = int(delay)
        new_entries.append(e)

    # Save generated file
    base_stem = Path(req.schedule_name).stem
    gen_name = f"{base_stem}_generated_{uuid.uuid4().hex[:6]}.json"
    gen_path = GENERATED_DIR / gen_name
    with gen_path.open("w", encoding="utf-8") as f:
        json.dump(new_entries, f, indent=4)

    model_entries = [ScheduleEntry(**e) for e in new_entries]

    return ScheduleGenerateResponse(
        generated_filename=gen_name,
        entries=model_entries,
    )


@app.post("/api/schedules/upload", response_model=UploadResponse)
def upload_and_run(req: UploadRequest):
    """
    Call schedular_script.py with the generated schedule file,
    then set up a "run" session for telemetry tracking.
    """
    schedule_path = GENERATED_DIR / req.generated_filename
    if not schedule_path.exists():
        raise HTTPException(status_code=404, detail="Generated schedule not found")

    script_path = BASE_DIR / "schedular_script.py"
    if not script_path.exists():
        raise HTTPException(
            status_code=500,
            detail="schedular_script.py not found in backend directory",
        )

    env = os.environ.copy()
    env["SCHEDULE_FILE"] = str(schedule_path)

    try:
        result = subprocess.run(
            [sys.executable, str(script_path), str(schedule_path)],
            cwd=str(BASE_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500, detail="Scheduler script timed out while running"
        )

    success = result.returncode == 0
    msg = "Scheduler script executed successfully" if success else "Scheduler script failed"

    # Load entries again to build command run table
    try:
        entries = load_schedule_file(schedule_path)
    except HTTPException:
        entries = []

    # Build run session
    run_id = str(uuid.uuid4())
    commands_internal: List[Dict[str, Any]] = []
    commands_api: List[CommandStatus] = []

    for idx, e in enumerate(entries):
        cmd_name: str = e.get("commandName", "")
        lut = str(e.get("LookUpTableID", ""))
        scheduled_ts = float(e.get("Timestamp", "0") or 0)
        delay = int(e.get("Delay", 0) or 0)

        # Map command -> telemetry name
        tm_name = (
            TELEMETRY_MAPPING.get(cmd_name)
            or TELEMETRY_MAPPING.get(cmd_name.upper())
            or TELEMETRY_MAPPING.get(cmd_name.lower())
        )

        internal = {
            "index": idx,
            "commandName": cmd_name,
            "lookUpTable": lut,
            "scheduledTimestamp": scheduled_ts,
            "delay": delay,
            "receivedTimestamp": None,
            "status": "SCHEDULED",
            "telemetry": None,
            "tm_name": tm_name,
        }
        commands_internal.append(internal)

        commands_api.append(
            CommandStatus(
                index=idx,
                commandName=cmd_name,
                lookUpTable=lut,
                scheduledTimestamp=scheduled_ts,
                delay=delay,
                receivedTimestamp=None,
                status="SCHEDULED",
                telemetry=None,
            )
        )

    RUNS[run_id] = {
        "created_at": now_epoch(),
        "schedule_file": str(schedule_path),
        "commands": commands_internal,
    }

    log_path = str((BASE_DIR / "output.txt").resolve())

    return UploadResponse(
        success=success,
        message=msg,
        log_path=log_path,
        stdout=result.stdout,
        stderr=result.stderr,
        run_id=run_id,
        commands=commands_api,
    )


@app.get("/api/runs/{run_id}", response_model=RunStatusResponse)
def get_run_status(run_id: str):
    """
    For a given run_id, poll OpenC3 for all mapped telemetry packets,
    update statuses based on timing, and return the current state.

    Logic per command:
    - Start as SCHEDULED.
    - Poll TM (if mapping exists).
    - If RECEIVED_TIMESECONDS within ±5 seconds of scheduledTimestamp => EXECUTED.
    - If now > scheduledTimestamp + 5 and still no match => FAILED.
    """
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    now = now_epoch()
    tol_sec = 10.0

    for cmd in run["commands"]:
        status = cmd.get("status", "SCHEDULED")
        if status in ("EXECUTED", "FAILED"):
            continue

        tm_name = cmd.get("tm_name")
        scheduled_ts = float(cmd.get("scheduledTimestamp", 0))

        if not tm_name:
            # No mapping: we can mark as FAILED quickly
            if now > scheduled_ts + tol_sec:
                cmd["status"] = "FAILED"
            continue

        # Poll OpenC3 for this TM
        fields = poll_tm_packet(tm_name)

        if fields is not None:
            recv_secs = fields.get("RECEIVED_TIMESECONDS") or fields.get(
                "PACKET_TIMESECONDS"
            )
            if isinstance(recv_secs, (int, float)):
                if abs(recv_secs - scheduled_ts) <= tol_sec:
                    cmd["status"] = "EXECUTED"
                    cmd["receivedTimestamp"] = float(recv_secs)
                    cmd["telemetry"] = fields

        # If still scheduled and we've passed scheduled_ts + tolerance, mark FAILED
        if cmd.get("status") == "SCHEDULED" and now > scheduled_ts + tol_sec:
            cmd["status"] = "FAILED"
            # receivedTimestamp stays None

    all_done = all(
        c.get("status") in ("EXECUTED", "FAILED") for c in run["commands"]
    )

    commands_api: List[CommandStatus] = []
    for c in run["commands"]:
        commands_api.append(
            CommandStatus(
                index=c["index"],
                commandName=c["commandName"],
                lookUpTable=c["lookUpTable"],
                scheduledTimestamp=float(c["scheduledTimestamp"]),
                delay=int(c["delay"]),
                receivedTimestamp=c.get("receivedTimestamp"),
                status=c.get("status", "SCHEDULED"),
                telemetry=c.get("telemetry"),
            )
        )

    return RunStatusResponse(run_id=run_id, all_done=all_done, commands=commands_api)
