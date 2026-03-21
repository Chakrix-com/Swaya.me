"""
Pydantic schemas for authentication
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional


class UserRegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    # tenant_name removed - tenant is auto-created per self-registration
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password complexity"""
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v


class UserLoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response"""
    id: int
    email: str
    full_name: Optional[str]
    tenant_id: int
    tenant_name: str
    tier: str
    is_active: bool
    role: Optional[str] = "user"  # Add role field
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TenantResponse(BaseModel):
    """Tenant response"""
    id: int
    name: str
    slug: str
    tier: str
    is_active: bool
    
    class Config:
        from_attributes = True


class ForgotPasswordRequest(BaseModel):
    """Password reset request (step 1)"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Password execution request (step 2)"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password complexity - mirroring UserRegisterRequest"""
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v
