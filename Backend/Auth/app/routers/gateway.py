from fastapi import APIRouter, Request, HTTPException
from app.gateway.proxy import proxy_request

router = APIRouter()

@router.api_route(
    "{full_path:path}",
    methods = ["GET","POST","PUT","PATCH","DELETE"]
)

async def gateway_handler(request:Request, full_path:str):
    user = request.state.user
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required for gateway access")
    return await proxy_request(request,user)
    