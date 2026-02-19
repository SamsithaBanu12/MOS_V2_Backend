from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.auth.security import decode_access_token

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.user = None
        if request.url.path.startswith("/auth") or request.url.path in ["/", "/health", "/docs", "/openapi.json"]:
            return await call_next(request)

        token = self.extract_token(request)
        if not token:
            return JSONResponse(status_code=401, content={"detail": "Missing authentication token"})
        
        user = decode_access_token(token)
        if not user:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})
        
        request.state.user = user 
        
        return await call_next(request)
    
    def extract_token(self, request: Request) -> str | None:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header.split(" ", 1)[1]
        
        return request.cookies.get("access_token")