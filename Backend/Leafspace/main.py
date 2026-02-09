import os
import time
import asyncio
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Body

from leafspace_client import LeafspaceClient

load_dotenv()

BASE_URL = os.getenv("LEAFSPACE_BASE_URL", "https://apiv2.sandbox.leaf.space")
USERNAME = os.getenv("LEAFSPACE_USERNAME", "")
PASSWORD = os.getenv("LEAFSPACE_PASSWORD", "")

POLL_SECONDS = 60 * 60  # 1 hour

app = FastAPI(title="Leafspace Backend (Sandbox/Prod via .env)")

client: Optional[LeafspaceClient] = None

# Cached list endpoints (polled hourly)
passages_cache: Dict[str, Any] = {"last_updated_epoch": None, "data": None, "error": None}
satellites_cache: Dict[str, Any] = {"last_updated_epoch": None, "data": None, "error": None}
groundstations_cache: Dict[str, Any] = {"last_updated_epoch": None, "data": None, "error": None}


async def poll_forever():
    global client, passages_cache, satellites_cache, groundstations_cache
    while True:
        try:
            data = await client.get_passages()  # type: ignore
            passages_cache.update({"data": data, "last_updated_epoch": time.time(), "error": None})
        except Exception as e:
            passages_cache["error"] = str(e)

        try:
            data = await client.get_satellites()  # type: ignore
            satellites_cache.update({"data": data, "last_updated_epoch": time.time(), "error": None})
        except Exception as e:
            satellites_cache["error"] = str(e)

        try:
            data = await client.get_groundstations()  # type: ignore
            groundstations_cache.update(
                {"data": data, "last_updated_epoch": time.time(), "error": None}
            )
        except Exception as e:
            groundstations_cache["error"] = str(e)

        await asyncio.sleep(POLL_SECONDS)


@app.on_event("startup")
async def startup():
    global client, passages_cache, satellites_cache, groundstations_cache
    client = LeafspaceClient(base_url=BASE_URL, username=USERNAME, password=PASSWORD)

    # initial fetch for cached lists
    try:
        passages_cache.update(
            {"data": await client.get_passages(), "last_updated_epoch": time.time(), "error": None}
        )
    except Exception as e:
        passages_cache["error"] = str(e)

    try:
        satellites_cache.update(
            {"data": await client.get_satellites(), "last_updated_epoch": time.time(), "error": None}
        )
    except Exception as e:
        satellites_cache["error"] = str(e)

    try:
        groundstations_cache.update(
            {
                "data": await client.get_groundstations(),
                "last_updated_epoch": time.time(),
                "error": None,
            }
        )
    except Exception as e:
        groundstations_cache["error"] = str(e)

    asyncio.create_task(poll_forever())


@app.on_event("shutdown")
async def shutdown():
    global client
    if client:
        await client.close()


# ----------------------------
# Cached list endpoints
# ----------------------------

@app.get("/api/passages")
async def api_get_passages():
    if passages_cache["data"] is None and passages_cache["error"] is not None:
        raise HTTPException(status_code=502, detail=passages_cache["error"])
    return passages_cache


@app.get("/api/satellites")
async def api_get_satellites():
    if satellites_cache["data"] is None and satellites_cache["error"] is not None:
        raise HTTPException(status_code=502, detail=satellites_cache["error"])
    return satellites_cache


@app.get("/api/groundstations")
async def api_get_groundstations():
    if groundstations_cache["data"] is None and groundstations_cache["error"] is not None:
        raise HTTPException(status_code=502, detail=groundstations_cache["error"])
    return groundstations_cache


# ----------------------------
# On-demand endpoints
# ----------------------------

@app.get("/api/passages/{passage_id}")
async def api_get_passage_detail(passage_id: str):
    global client
    if not client:
        raise HTTPException(status_code=500, detail="Client not ready")
    return await client.get_passage_detail(passage_id)


@app.get("/api/passages/{passage_id}/log")
async def api_get_passage_log(passage_id: str):
    """
    GET /passages/{passage_id}/log
    """
    global client
    if not client:
        raise HTTPException(status_code=500, detail="Client not ready")
    return await client.get_passage_log(passage_id)


@app.delete("/api/passages/{passage_id}")
async def api_delete_passage(passage_id: str):
    global client
    if not client:
        raise HTTPException(status_code=500, detail="Client not ready")
    return await client.delete_passage(passage_id)


@app.get("/api/passages/candidates")
async def api_get_passage_candidates(
    satelliteID: Optional[str] = Query(None, description="Satellite ID"),
    groundStationID: Optional[str] = Query(None, description="Ground Station ID"),
):
    global client
    if not client:
        raise HTTPException(status_code=500, detail="Client not ready")
    return await client.get_passage_candidates(
        satellite_id=satelliteID,
        groundstation_id=groundStationID,
    )


@app.post("/api/passages/candidates/book")
async def api_book_passage_candidates(
    allow_overlap: bool = Query(False, description="Leafspace allow_overlap query param"),
    body: Dict[str, Any] = Body(..., description="Bookings JSON keyed by candidateId"),
):
    global client
    if not client:
        raise HTTPException(status_code=500, detail="Client not ready")
    return await client.book_passage_candidates(bookings=body, allow_overlap=allow_overlap)


@app.get("/api/satellites/{satellite_id}")
async def api_get_satellite_detail(satellite_id: str):
    global client
    if not client:
        raise HTTPException(status_code=500, detail="Client not ready")
    return await client.get_satellite_detail(satellite_id)


@app.get("/api/satellites/{satellite_id}/forbiddenwindows")
async def api_get_satellite_forbidden_windows(satellite_id: str):
    global client
    if not client:
        raise HTTPException(status_code=500, detail="Client not ready")
    return await client.get_satellite_forbidden_windows(satellite_id)


# ----------------------------
# TLE endpoints
# ----------------------------

@app.get("/api/tle")
async def api_get_tle():
    global client
    if not client:
        raise HTTPException(status_code=500, detail="Client not ready")
    return await client.get_tle()


@app.post("/api/tle")
async def api_post_tle(tle_text: str = Body(..., media_type="text/plain")):
    """
    Frontend sends raw TLE text in request body (text/plain).
    Backend forwards as Content-Type: application/text to Leafspace (per curl).
    """
    global client
    if not client:
        raise HTTPException(status_code=500, detail="Client not ready")
    return await client.post_tle(tle_text)


@app.delete("/api/tle/{satellite_id}")
async def api_delete_tle(satellite_id: str):
    global client
    if not client:
        raise HTTPException(status_code=500, detail="Client not ready")
    return await client.delete_tle(satellite_id)


@app.get("/api/token/status")
async def api_token_status():
    global client
    if not client:
        raise HTTPException(status_code=500, detail="Client not ready")
    await client.get_token()
    return {"base_url": BASE_URL, **client.token_status()}
