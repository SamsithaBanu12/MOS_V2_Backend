import time
import base64
import asyncio
from typing import Any, Optional, Dict

import httpx
from fastapi import HTTPException


class LeafspaceClient:
    """
    - Base64 encodes username:password
    - Fetches OAuth token via multipart form (matches curl -F)
    - Uses Bearer token for API calls
    - Auto-refreshes token when expired
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        token_refresh_buffer_seconds: int = 60,
    ):
        if not base_url:
            raise ValueError("base_url is required")
        if not username or not password:
            raise ValueError("Missing Leafspace username/password")

        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password

        self.token_url = f"{self.base_url}/oauth2/token"

        self.passages_url = f"{self.base_url}/passages"
        self.satellites_url = f"{self.base_url}/satellites"
        self.groundstations_url = f"{self.base_url}/groundstations"
        self.tle_url = f"{self.base_url}/tle"

        self._token_refresh_buffer_seconds = token_refresh_buffer_seconds

        self._token: Optional[str] = None
        self._expires_at_epoch: float = 0.0
        self._lock = asyncio.Lock()

        self._http = httpx.AsyncClient(timeout=30)

    async def close(self):
        await self._http.aclose()

    def _basic_auth_string(self) -> str:
        raw = f"{self.username}:{self.password}".encode("utf-8")
        return base64.b64encode(raw).decode("utf-8")

    def _token_valid(self) -> bool:
        return (
            self._token is not None
            and time.time() < (self._expires_at_epoch - self._token_refresh_buffer_seconds)
        )

    async def get_token(self) -> str:
        async with self._lock:
            if self._token_valid():
                return self._token  # type: ignore

            auth_string = self._basic_auth_string()
            headers = {"Authorization": f"Basic {auth_string}"}
            files = {"grant_type": (None, "client_credentials")}

            resp = await self._http.post(self.token_url, headers=headers, files=files)
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Token request failed ({resp.status_code}): {resp.text}",
                )

            payload = resp.json()
            token = payload.get("access_token")
            expires_in = float(payload.get("expires_in", 86400))

            if not token:
                raise HTTPException(status_code=502, detail=f"Invalid token response: {payload}")

            self._token = token
            self._expires_at_epoch = time.time() + expires_in
            return token

    async def _auth_headers(
        self,
        accept: Optional[str] = "application/json",
        content_type: Optional[str] = None,
    ) -> Dict[str, str]:
        token = await self.get_token()
        headers: Dict[str, str] = {"Authorization": f"Bearer {token}"}
        if accept:
            headers["accept"] = accept
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    async def _retry_if_unauthorized(self):
        async with self._lock:
            self._token = None
            self._expires_at_epoch = 0.0

    async def _get_json(self, url: str) -> Any:
        headers = await self._auth_headers(accept="application/json")
        resp = await self._http.get(url, headers=headers)

        if resp.status_code in (401, 403):
            await self._retry_if_unauthorized()
            headers = await self._auth_headers(accept="application/json")
            resp = await self._http.get(url, headers=headers)

        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Leafspace GET failed ({resp.status_code}) for {url}: {resp.text}",
            )

        return resp.json()

    async def _post_json(self, url: str, payload: Any) -> Any:
        headers = await self._auth_headers(accept="application/json", content_type="application/json")
        resp = await self._http.post(url, headers=headers, json=payload)

        if resp.status_code in (401, 403):
            await self._retry_if_unauthorized()
            headers = await self._auth_headers(accept="application/json", content_type="application/json")
            resp = await self._http.post(url, headers=headers, json=payload)

        if resp.status_code < 200 or resp.status_code >= 300:
            raise HTTPException(
                status_code=502,
                detail=f"Leafspace POST failed ({resp.status_code}) for {url}: {resp.text}",
            )

        if not resp.text.strip():
            return {"status_code": resp.status_code}
        return resp.json()

    async def _post_text(self, url: str, text_body: str, content_type: str) -> Any:
        """
        Used for POST /tle where Content-Type is application/text (per your curl)
        """
        if text_body is None or not str(text_body).strip():
            raise HTTPException(status_code=400, detail="Body must be non-empty text")

        headers = await self._auth_headers(accept="application/json", content_type=content_type)
        resp = await self._http.post(url, headers=headers, content=text_body)

        if resp.status_code in (401, 403):
            await self._retry_if_unauthorized()
            headers = await self._auth_headers(accept="application/json", content_type=content_type)
            resp = await self._http.post(url, headers=headers, content=text_body)

        if resp.status_code < 200 or resp.status_code >= 300:
            raise HTTPException(
                status_code=502,
                detail=f"Leafspace POST (text) failed ({resp.status_code}) for {url}: {resp.text}",
            )

        if not resp.text.strip():
            return {"status_code": resp.status_code}

        # If Leafspace returns JSON, parse it; else return raw text
        try:
            return resp.json()
        except Exception:
            return {"status_code": resp.status_code, "text": resp.text}

    async def _delete(self, url: str) -> Any:
        headers = await self._auth_headers(accept="application/json")
        resp = await self._http.delete(url, headers=headers)

        if resp.status_code in (401, 403):
            await self._retry_if_unauthorized()
            headers = await self._auth_headers(accept="application/json")
            resp = await self._http.delete(url, headers=headers)

        if resp.status_code < 200 or resp.status_code >= 300:
            raise HTTPException(
                status_code=502,
                detail=f"Leafspace DELETE failed ({resp.status_code}) for {url}: {resp.text}",
            )

        if not resp.text.strip():
            return {"status_code": resp.status_code}
        return resp.json()

    # ----------------------------
    # POLLED LIST ENDPOINTS
    # ----------------------------
    async def get_passages(self) -> Any:
        return await self._get_json(self.passages_url)

    async def get_satellites(self) -> Any:
        return await self._get_json(self.satellites_url)

    async def get_groundstations(self) -> Any:
        return await self._get_json(self.groundstations_url)

    # ----------------------------
    # ON-DEMAND GET ENDPOINTS
    # ----------------------------
    async def get_satellite_detail(self, satellite_id: str) -> Any:
        satellite_id = satellite_id.strip()
        if not satellite_id:
            raise HTTPException(status_code=400, detail="satellite_id is required")
        return await self._get_json(f"{self.satellites_url}/{satellite_id}")

    async def get_satellite_forbidden_windows(self, satellite_id: str) -> Any:
        satellite_id = satellite_id.strip()
        if not satellite_id:
            raise HTTPException(status_code=400, detail="satellite_id is required")
        return await self._get_json(f"{self.satellites_url}/{satellite_id}/forbiddenwindows")

    async def get_passage_detail(self, passage_id: str) -> Any:
        passage_id = passage_id.strip()
        if not passage_id:
            raise HTTPException(status_code=400, detail="passage_id is required")
        return await self._get_json(f"{self.passages_url}/{passage_id}")

    async def get_passage_log(self, passage_id: str) -> Any:
        """
        GET /passages/{passage_id}/log
        """
        passage_id = passage_id.strip()
        if not passage_id:
            raise HTTPException(status_code=400, detail="passage_id is required")
        return await self._get_json(f"{self.passages_url}/{passage_id}/log")

    async def get_passage_candidates(
        self,
        satellite_id: Optional[str] = None,
        groundstation_id: Optional[str] = None,
    ) -> Any:
        params: Dict[str, str] = {}
        if satellite_id:
            params["satelliteID"] = satellite_id.strip()
        if groundstation_id:
            params["groundStationID"] = groundstation_id.strip()

        if params:
            qs = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{self.passages_url}/candidates?{qs}"
        else:
            url = f"{self.passages_url}/candidates"

        return await self._get_json(url)

    async def get_tle(self) -> Any:
        """
        GET /tle
        """
        return await self._get_json(self.tle_url)

    # ----------------------------
    # ON-DEMAND POST/DELETE ENDPOINTS
    # ----------------------------
    async def book_passage_candidates(
        self,
        bookings: Dict[str, Any],
        allow_overlap: bool = False,
    ) -> Any:
        if not isinstance(bookings, dict) or not bookings:
            raise HTTPException(status_code=400, detail="Request body must be a non-empty JSON object")

        allow_str = "true" if allow_overlap else "false"
        url = f"{self.passages_url}/candidates/book?allow_overlap={allow_str}"
        return await self._post_json(url, bookings)

    async def delete_passage(self, passage_id: str) -> Any:
        """
        DELETE /passages/{passage_id}
        """
        passage_id = passage_id.strip()
        if not passage_id:
            raise HTTPException(status_code=400, detail="passage_id is required")
        return await self._delete(f"{self.passages_url}/{passage_id}")

    async def post_tle(self, tle_text: str) -> Any:
        """
        POST /tle with Content-Type: application/text (per your curl).
        """
        return await self._post_text(self.tle_url, tle_text, content_type="application/text")

    async def delete_tle(self, satellite_id: str) -> Any:
        """
        DELETE /tle/{satellite_id}
        """
        satellite_id = satellite_id.strip()
        if not satellite_id:
            raise HTTPException(status_code=400, detail="satellite_id is required")
        return await self._delete(f"{self.tle_url}/{satellite_id}")

    def token_status(self) -> dict:
        now = time.time()
        return {
            "has_token": self._token is not None,
            "seconds_until_expiry": max(int(self._expires_at_epoch - now), 0),
            "expires_at_epoch": self._expires_at_epoch,
        }
