from fastapi import APIRouter, Request, HTTPException, WebSocket
from app.gateway.proxy import proxy_request
from app.gateway.ws_proxy import proxy_websocket
from app.auth.security import decode_access_token

router = APIRouter()

@router.websocket("{full_path:path}")
async def websocket_gateway_handler(websocket: WebSocket, full_path: str):
    # Auth check for WebSockets (using cookies)
    token = websocket.cookies.get("access_token")
    if not token:
        # 4001 is a custom code for Auth Required
        await websocket.close(code=4001) 
        return
    
    user = decode_access_token(token)
    if not user:
        await websocket.close(code=4001)
        return
        
    await proxy_websocket(websocket, user)

@router.api_route(
    "{full_path:path}",
    methods = ["GET","POST","PUT","PATCH","DELETE"]
)
async def gateway_handler(request: Request, full_path: str):
    user = request.state.user
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required for gateway access")
    return await proxy_request(request, user)