from fastapi import Depends, HTTPException, status, Request
from typing import List, Dict, Any
from app.auth.security import decode_access_token

async def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Dependency to get the current authenticated user from request state or token.
    """
    # Try getting from request.state (populated by middleware for non-/auth routes)
    user = getattr(request.state, "user", None)
    
    if user:
        return user
        
    # If not in request.state (e.g. /auth routes), check Authorization header manually
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = auth_header.split(" ", 1)[1]
    user = decode_access_token(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = [role.lower() for role in allowed_roles]

    def __call__(self, user: Dict[str, Any] = Depends(get_current_user)):
        user_role = user.get("role", "").lower()
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role: {user.get('role')}. Required: {self.allowed_roles}"
            )
        return user
