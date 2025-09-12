from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from app.models.user import UserRole

class UserEmailCreate(BaseModel):
    email: EmailStr
    is_primary: bool = False

class UserEmailResponse(BaseModel):
    id: int
    email: str
    is_primary: bool
    is_verified: bool
    verified_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str
    full_name: str
    emails: List[UserEmailCreate]
    password: Optional[str] = None
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if len(v) > 30:
            raise ValueError('Username must be less than 30 characters')
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v.lower()
    
    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Full name must be at least 2 characters long')
        return v.strip()
    
    @field_validator('emails')
    @classmethod
    def validate_emails(cls, v):
        if not v:
            raise ValueError('At least one email is required')
        
        primary_count = sum(1 for email in v if email.is_primary)
        if primary_count > 1:
            raise ValueError('Only one email can be marked as primary')
        
        return v
    
class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None    

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    emails: List[UserEmailResponse]
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class GoogleAuthRequest(BaseModel):
    authorization_code: str