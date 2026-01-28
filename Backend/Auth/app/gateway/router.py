# Path → service resolution
from fastapi import HTTPException

SERVICE_ROUTES = {
    "/api/fileupload": "http://file-upload:8080"
}

def resolve_service(path:str) -> tuple[str, str]:
    for prefix, service_url in SERVICE_ROUTES.items():
        if path.startswith(prefix):
            return service_url, prefix
    
    raise HTTPException(status_code=404, detail="Service not found")