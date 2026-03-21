"""
Organization management schemas
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
import re


class OrganizationCreateRequest(BaseModel):
    """Request to create a new organization"""
    name: str = Field(..., min_length=2, max_length=255)
    slug: Optional[str] = Field(None, min_length=2, max_length=100)
    tier: str = Field(default="free")
    
    @validator('tier')
    def validate_tier(cls, v):
        """Validate tier is one of allowed values"""
        allowed = ['free', 'basic', 'pro', 'enterprise']
        if v.lower() not in allowed:
            raise ValueError(f'Tier must be one of: {", ".join(allowed)}')
        return v.lower()
    
    @validator('slug')
    def validate_slug(cls, v):
        """Validate slug format"""
        if v is not None:
            if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', v):
                raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
        return v


class OrganizationUpdateRequest(BaseModel):
    """Request to update organization details"""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    tier: Optional[str] = None
    is_active: Optional[bool] = None
    
    @validator('tier')
    def validate_tier(cls, v):
        if v is not None:
            allowed = ['free', 'basic', 'pro', 'enterprise']
            if v.lower() not in allowed:
                raise ValueError(f'Tier must be one of: {", ".join(allowed)}')
            return v.lower()
        return v


class OrganizationResponse(BaseModel):
    """Organization response"""
    id: int
    name: str
    slug: str
    tier: str
    is_active: bool
    created_at: str
    updated_at: str
    user_count: Optional[int] = 0
    admin_count: Optional[int] = 0
    
    class Config:
        from_attributes = True


class AdminUserCreateRequest(BaseModel):
    """Request to create an admin user for an organization"""
    email: str
    full_name: Optional[str] = Field(None, max_length=255)
    password: str = Field(..., min_length=8, max_length=100)
    tenant_id: int
    user_quota: int = Field(default=10, ge=1, le=10000)
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password complexity"""
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v


class AdminUserResponse(BaseModel):
    """Admin user response with quota info"""
    id: int
    email: str
    full_name: Optional[str]
    tenant_id: int
    tenant_name: str
    role: str
    user_quota: Optional[int]
    quota_usage: Optional[int] = 0
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True


class UpdateQuotaRequest(BaseModel):
    """Request to update admin user quota"""
    user_quota: int = Field(..., ge=1, le=10000)
