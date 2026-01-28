# HTTP forwarding logic
from fastapi import HTTPException
import httpx 
from fastapi import Request, Response

from .headers import build_forward_headers
from .router import resolve_service

from fastapi.responses import StreamingResponse

async def proxy_request(request: Request, user: dict) -> Response:
    target_base, prefix = resolve_service(request.url.path)
    
    # Strip prefix and join with target base
    sub_path = request.url.path[len(prefix):].lstrip("/")
    target_url = target_base.rstrip('/')
    if sub_path:
        target_url += f"/{sub_path}"
    
    if request.query_params:
        target_url += f"?{request.query_params}"

    try:
        client = httpx.AsyncClient(timeout=None) # No timeout for streaming
        
        # We must get the response headers and status code FIRST.
        req_headers = build_forward_headers(request.headers, user)
        
        req = client.build_request(
            method=request.method,
            url=target_url,
            content=request.stream(),
            headers=req_headers
        )
        
        resp = await client.send(req, stream=True)
        
        return StreamingResponse(
            resp.aiter_bytes(),
            status_code=resp.status_code,
            headers=filter_response_headers(resp.headers),
            background=lambda: client.aclose()
        )

    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Service unavailable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Service timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gateway Error: {str(e)}")

def filter_response_headers(headers:dict) -> dict:
    excluded = {"content-length","transfer-encoding", "connection"}
    return {k:v for k, v in headers.items() if k.lower() not in excluded}