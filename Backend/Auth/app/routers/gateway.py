from fastapi import APIRouter, Request, HTTPException
from app.gateway.proxy import proxy_request

router = APIRouter()

SERVICE_ROUTES = {
    "/api/fileupload": "http://file-upload:8080",
    "/api/schedules": "http://schedule-upload:8008/api/schedules",
    "/api/runs": "http://schedule-upload:8008/api/runs",
    "/api/bridge": "http://bridge-backend:8002",
    "/openc3-api": "http://openc3-traefik:2900/openc3-api"
}

@router.api_route(
    "{full_path:path}",
    methods = ["GET","POST","PUT","PATCH","DELETE"]
)

async def gateway_handler(request:Request, full_path:str):
    user = request.state.user
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required for gateway access")
    return await proxy_request(request,user)