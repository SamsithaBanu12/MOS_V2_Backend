from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from app.database import get_db
from app.models.user import User, Role, RefreshToken
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, TokenRefreshRequest, RoleUpdateRequest, UserResponse
from app.auth.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_access_token
from app.auth.dependencies import get_current_user, RoleChecker
from app.config import settings


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/users", response_model=List[UserResponse])
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RoleChecker(["ADMIN", "SUPER_ADMIN"]))
) -> List[UserResponse]:
    """
    List users with role-based visibility:
    - SUPER_ADMIN: Can see all users.
    - ADMIN: Can see all users except SUPER_ADMIN.
    """
    # Force load current_user's role if not already present
    from sqlalchemy.orm import selectinload
    result = await db.execute(select(User).where(User.id == current_user.id).options(selectinload(User.role)))
    current_user = result.scalar_one()

    # Build query
    query = select(User).options(selectinload(User.role))

    if current_user.role.name == "ADMIN":
        # Admins cannot see Super Admins
        query = query.join(Role).where(Role.name != "SUPER_ADMIN")
    
    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [
        UserResponse(
            id=str(u.id),
            email=u.email,
            username=u.username,
            role=u.role.name,
            is_active=u.is_active,
            created_at=u.created_at.isoformat() if u.created_at else None
        )
        for u in users
    ]


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Register a new user account.
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Find or validate role
    result = await db.execute(select(Role).where(Role.name == request.role))
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{request.role}' not found"
        )
    
    # Hash password
    hashed_password = hash_password(request.password)
    
    # Create new user
    new_user = User(
        email=request.email,
        username=request.username,
        password_hash=hashed_password,
        role_id=role.id,
        is_active=True
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return {
        "message": "User registered successfully",
        "user": {
            "id": str(new_user.id),
            "email": new_user.email,
            "username": new_user.username,
            "role": request.role
        }
    }


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Authenticate user and generate access and refresh tokens.
    """
    # Fetch user with role and permissions
    result = await db.execute(
        select(User)
        .where(User.email == request.email)
        .options(selectinload(User.role).selectinload(Role.permissions))
    )
    user = result.scalar_one_or_none()
    
    # Validate user exists
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Extract role and permissions
    role_name = user.role.name
    permissions = [perm.name for perm in user.role.permissions]
    
    # Create Access Token
    token_data = {
        "user_id": str(user.id),
        "username": user.username,
        "role": role_name,
        "permissions": permissions,
        "type": "access"
    }
    access_token = create_access_token(token_data)
    
    # Create Refresh Token
    refresh_token_str = create_refresh_token({"user_id": str(user.id)})
    
    # Save refresh token to DB
    db_refresh_token = RefreshToken(
        token=refresh_token_str,
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(db_refresh_token)
    await db.commit()
    
    return TokenResponse(
        username=user.username,
        email=user.email,
        access_token=access_token,
        refresh_token=refresh_token_str,
        role=role_name,
        permissions=permissions
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Renew access token using a refresh token.
    Uses 'Refresh Token Rotation' for enhanced security.
    """
    # 1. Decode and validate the token structure
    payload = decode_access_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # 2. Check database for token and its status
    result = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.token == request.refresh_token)
        .where(RefreshToken.is_revoked == False)
    )
    db_token = result.scalar_one_or_none()
    
    if not db_token or db_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired or revoked"
        )
    
    # 3. Fetch user and their permissions
    result = await db.execute(
        select(User)
        .where(User.id == db_token.user_id)
        .options(selectinload(User.role).selectinload(Role.permissions))
    )
    user = result.scalar_one()
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # 4. Invalidate old token (Rotation)
    db_token.is_revoked = True
    
    # 5. Generate new tokens
    role_name = user.role.name
    permissions = [p.name for p in user.role.permissions]
    
    new_access_token = create_access_token({
        "user_id": str(user.id),
        "username": user.username,
        "role": role_name,
        "permissions": permissions,
        "type": "access"
    })
    new_refresh_token_str = create_refresh_token({"user_id": str(user.id)})
    
    # 6. Save new refresh token
    new_db_token = RefreshToken(
        token=new_refresh_token_str,
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(new_db_token)
    await db.commit()
    
    return TokenResponse(
        username=user.username,
        email=user.email,
        access_token=new_access_token,
        refresh_token=new_refresh_token_str,
        role=role_name,
        permissions=permissions
    )


@router.post("/logout")
async def logout(
    request: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke a refresh token to log out.
    """
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == request.refresh_token)
    )
    db_token = result.scalar_one_or_none()
    
    if db_token:
        db_token.is_revoked = True
        await db.commit()
        
    return {"message": "Logged out successfully"}


@router.post("/update-role", status_code=status.HTTP_200_OK)
async def update_user_role(
    request: RoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Update a user's role. Restricted to SUPER_ADMIN and ADMIN.
    """
    # 1. Fetch current user's role name
    result = await db.execute(select(Role).where(Role.id == current_user.role_id))
    current_role = result.scalar_one()
    
    # 2. Check if current user is authorized (SUPER_ADMIN or ADMIN)
    if current_role.name not in ["SUPER_ADMIN", "ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update roles"
        )
    
    # 3. Fetch the user to be updated
    result = await db.execute(select(User).where(User.id == request.user_id))
    user_to_update = result.scalar_one_or_none()
    
    if not user_to_update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 4. Fetch the new role
    result = await db.execute(select(Role).where(Role.name == request.new_role))
    new_role = result.scalar_one_or_none()
    
    if not new_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{request.new_role}' does not exist"
        )
        
    # 5. Security check: ADMIN cannot create a SUPER_ADMIN
    if current_role.name == "ADMIN" and new_role.name == "SUPER_ADMIN":
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrators cannot promote users to SUPER_ADMIN"
        )

    # 6. Update user role
    user_to_update.role_id = new_role.id
    await db.commit()
    
    return {
        "message": f"Successfully updated user {user_to_update.username}'s role to {new_role.name}",
        "user_id": str(user_to_update.id),
        "new_role": new_role.name
    }