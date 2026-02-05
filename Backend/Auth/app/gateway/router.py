# Path → service resolution
from fastapi import HTTPException

SERVICE_ROUTES = {
    "/api/fileupload": "http://file-upload:8080",
    "/api/schedules": "http://schedule-upload:8008/api/schedules",
    "/api/runs": "http://schedule-upload:8008/api/runs",
    "/api/bridge": "http://bridge-backend:8002",
    "/api/openc3-api/api": "http://openc3-cosmos-cmd-tlm-api:2901/openc3-api/api"
}

def resolve_service(path:str) -> tuple[str, str]:
    for prefix, service_url in SERVICE_ROUTES.items():
        if path.startswith(prefix):
            return service_url, prefix
    
    raise HTTPException(status_code=404, detail="Service not found")