import asyncio
import websockets
from fastapi import WebSocket, WebSocketDisconnect
from .router import resolve_service

async def proxy_websocket(websocket: WebSocket, user: dict):
    """
    Proxy WebSocket connections from client to internal services.
    """
    path = websocket.url.path
    
    try:
        target_base, prefix = resolve_service(path)
    except Exception:
        await websocket.close(code=1011) # Internal Error
        return

    # Convert http:// to ws:// for the target
    ws_target_base = target_base.replace("http://", "ws://").replace("https://", "wss://")
    
    # Strip prefix and join with target base
    sub_path = path[len(prefix):].lstrip("/")
    target_url = ws_target_base.rstrip('/')
    if sub_path:
        target_url += f"/{sub_path}"
    
    if websocket.query_params:
        target_url += f"?{websocket.query_params}"

    # Prepare headers
    raw_role = user.get("role", "")
    
    # Map roles for Grafana (Exact match for SUPER_ADMIN, ADMIN, MISSION_OPERATOR)
    if raw_role in ["SUPER_ADMIN", "ADMIN", "MISSION_OPERATOR"]:
        grafana_role = "Admin"
    else:
        grafana_role = "Viewer"

    headers = [
        ("X-WEBAUTH-USER", user.get("username", str(user["user_id"]))),
        ("X-WEBAUTH-ROLE", grafana_role),
        ("X-User-Id", str(user["user_id"])),
        ("X-User-Roles", raw_role)
    ]

    try:
        async with websockets.connect(target_url, extra_headers=headers) as target_ws:
            await websocket.accept()

            async def client_to_target():
                try:
                    while True:
                        data = await websocket.receive_text()
                        await target_ws.send(data)
                except Exception:
                    pass

            async def target_to_client():
                try:
                    while True:
                        try:
                            data = await target_ws.recv()
                            await websocket.send_text(data)
                        except websockets.ConnectionClosed:
                            break
                except Exception:
                    pass

            # Run both directions concurrently
            await asyncio.gather(client_to_target(), target_to_client())

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket Gateway Error: {e}")
        try:
            await websocket.close(code=1011)
        except:
            pass
