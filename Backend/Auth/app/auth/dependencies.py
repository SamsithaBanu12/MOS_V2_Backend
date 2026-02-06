from typing import List, Callable,Dict,Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.user import User, Role, Permission
from app.auth.security import decode_access_token


# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to extract and validate the current user from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        db: Database session
        
    Returns:
        Current authenticated user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    
    # Decode token
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract user_id from payload
    user_id: str = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Fetch user from database with role eagerly loaded
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.role))
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


def require_permission(permission_name: str) -> Callable:
    """
    Dependency factory to check if the current user has a specific permission.
    
    Usage:
        @router.get("/admin", dependencies=[Depends(require_permission("admin_access"))])
        async def admin_endpoint():
            return {"message": "Admin access granted"}
    
    Args:
        permission_name: Name of the required permission
        
    Returns:
        Dependency function that validates permission
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        """
        Check if current user has the required permission.
        
        Args:
            current_user: Current authenticated user
            db: Database session
            
        Returns:
            Current user if permission check passes
            
        Raises:
            HTTPException: If user lacks required permission
        """
        # Fetch user's role with permissions
        result = await db.execute(
            select(Role)
            .where(Role.id == current_user.role_id)
            .options(selectinload(Role.permissions))
        )
        role = result.scalar_one_or_none()
        
        if role is None:
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
        
        return current_user
    
    return permission_checker

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