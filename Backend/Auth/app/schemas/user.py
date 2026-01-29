from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    """User response schema."""
    
    id: UUID
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}
