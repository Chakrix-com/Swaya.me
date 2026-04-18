"""
User Management Schemas
Pydantic models for user management API requests/responses
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from persistence.models.core import UserRole, TierEnum


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.user
    tenant_id: Optional[int] = None  # Optional - super admin can set, others use their own


class UserUpdate(BaseModel):
    """Schema for updating user details"""
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


class UserPasswordUpdate(BaseModel):
    """Schema for password updates"""
    current_password: str
    new_password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    """User response with all details"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    role: UserRole
    is_active: bool
    last_login_at: Optional[datetime] = None
    login_count: int
    created_at: datetime
    updated_at: datetime
    tier: Optional[str] = None
    tenant_name: Optional[str] = None


class UserListResponse(BaseModel):
    """Paginated user list response"""
    users: List[UserResponse]
    total: int
    page: int
    per_page: int
    pages: int


# User Statistics
class UserStats(BaseModel):
    """User statistics"""
    total_logins: int
    last_login: Optional[datetime]
    quizzes_created: int
    total_participants: int


# Activity Log Schemas
class ActivityLogResponse(BaseModel):
    """Activity log entry"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    action: str
    resource_type: Optional[str]
    resource_id: Optional[int]
    details: Optional[dict]
    ip_address: Optional[str]
    created_at: datetime


class ActivityLogListResponse(BaseModel):
    """Paginated activity log"""
    activities: List[ActivityLogResponse]
    total: int
    page: int
    per_page: int


# Tenant Management (Super Admin)
class TenantResponse(BaseModel):
    """Tenant details"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    tier: TierEnum
    is_active: bool
    user_count: int
    created_at: datetime


class TenantUpdate(BaseModel):
    """Update tenant settings"""
    name: Optional[str] = None
    tier: Optional[TierEnum] = None
    is_active: Optional[bool] = None


class TenantListResponse(BaseModel):
    """Paginated tenant list"""
    tenants: List[TenantResponse]
    total: int
    page: int
    per_page: int
