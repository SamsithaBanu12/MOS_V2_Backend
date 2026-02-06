from typing import List, Callable,Dict,Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.user import User, Role, Permission
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
    
    # Fetch user from database with role eagerly loaded
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.role))
    )
    user = result.scalar_one_or_none()
    
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
                detail="User role not found"
            )
        
        # Check if permission exists in user's role
        user_permissions = [perm.name for perm in role.permissions]
        
        if permission_name not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required permission: {permission_name}"
            )
        return user

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = [role.lower() for role in allowed_roles]

    async def __call__(
        self, 
        user: User = Depends(get_current_user)
    ) -> User:
        """
        Check role and return user if authorized. 
        Role is pre-loaded by get_current_user using selectinload.
        """
        user_role = user.role.name.lower()
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role: {user.role.name}. Required: {self.allowed_roles}"
            )
        return user