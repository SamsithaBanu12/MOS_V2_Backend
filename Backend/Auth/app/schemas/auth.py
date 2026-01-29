from typing import List
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request schema."""
    
    email: EmailStr
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    """Registration request schema."""
    
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=100)
    role: str = Field(..., min_length=1, max_length=50)


class TokenResponse(BaseModel):
    """Token response schema after successful login."""
    
    username: str
    email: str
    token: str
    role: str
    permissions: List[str]
