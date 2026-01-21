from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.user import User, Role, Permission
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.auth.security import hash_password, verify_password, create_access_token


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Register a new user account.
    
    Args:
        request: Registration request with email, username, password, and role
        db: Database session
        
    Returns:
        Success message with user details
        
    Raises:
        HTTPException: If email already exists or role not found
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
    Authenticate user and generate JWT token.
    
    Args:
        request: Login request with email and password
        db: Database session
        
    Returns:
        Token response with user details and JWT token
        
    Raises:
        HTTPException: If credentials are invalid
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
    
    # Create JWT token
    token_data = {
        "user_id": str(user.id),
        "role": role_name,
        "permissions": permissions
    }
    access_token = create_access_token(token_data)
    
    return TokenResponse(
        username=user.username,
        email=user.email,
        token=access_token,
        role=role_name,
        permissions=permissions
    )
