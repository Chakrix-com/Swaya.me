"""
Core domain models for multi-tenant architecture
"""
from sqlalchemy import Column, Integer, String, Boolean, Enum as SQLEnum, ForeignKey, Text, DateTime, JSON
from sqlalchemy.orm import relationship
import enum

from persistence.database import Base
from persistence.models.base import TimestampMixin


class TierEnum(str, enum.Enum):
    """Subscription tier types"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class UserRole(str, enum.Enum):
    """User roles for access control"""
    super_admin = "super_admin"  # Platform-level admin (tenant_id=1)
    admin = "admin"              # Tenant-level admin
    user = "user"                # Regular user (can create quizzes)
    viewer = "viewer"            # Read-only access


class Tenant(Base, TimestampMixin):
    """
    Tenant entity - represents an organization/account
    All data in the system is scoped to a tenant
    """
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    tier = Column(SQLEnum(TierEnum), default=TierEnum.FREE, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    users = relationship("User", back_populates="tenant")
    events = relationship("Event", back_populates="tenant")


class User(Base, TimestampMixin):
    """
    User entity - represents a host/admin user
    Tied to a specific tenant
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.user, server_default="user")
    
    # Email Verification
    is_email_verified = Column(Boolean, default=False, nullable=False, server_default="0")
    email_verification_token = Column(String(255), nullable=True)
    
    # Password Reset
    reset_password_token = Column(String(255), unique=True, nullable=True)
    reset_password_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Activity tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, nullable=False, default=0, server_default="0")
    
    # Admin quota system (for admin role only)
    user_quota = Column(Integer, nullable=True)  # Max users this admin can create
    managed_by_admin_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)  # Which admin owns this user
    
    # Language preference
    language_preference = Column(String(10), nullable=False, default='en', server_default='en')
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    events = relationship("Event", back_populates="creator")
    activities = relationship("UserActivity", back_populates="user", cascade="all, delete-orphan")
    managed_by_admin = relationship("User", remote_side=[id], foreign_keys=[managed_by_admin_id])


class Event(Base, TimestampMixin):
    """
    Event entity - represents a live event/quiz session
    Events are tenant-scoped
    """
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False, index=True)
    creator_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    join_code = Column(String(10), unique=True, nullable=True, index=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="events")
    creator = relationship("User", back_populates="events")


class UserActivity(Base):
    """
    User activity log for audit trail
    Tracks user actions across the platform
    """
    __tablename__ = "user_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP", nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="activities")


class TierConfiguration(Base, TimestampMixin):
    """
    Tier configuration - defines limits and features per tier
    """
    __tablename__ = "tier_configurations"

    id = Column(Integer, primary_key=True, index=True)
    tier = Column(SQLEnum(TierEnum), unique=True, nullable=False)
    max_participants = Column(Integer, nullable=False)
    max_questions = Column(Integer, nullable=False)
    max_concurrent_events = Column(Integer, nullable=False)
    features = Column(Text, nullable=True)  # JSON string of enabled features


class EventTypeEnum(str, enum.Enum):
    """Language event types"""
    INITIAL = "initial"
    CHANGE = "change"


class LanguageUsageEvent(Base):
    """
    Language usage tracking - logs all language selection events
    Tracks both authenticated and anonymous users
    """
    __tablename__ = "language_usage_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    session_id = Column(String(100), nullable=True, index=True)
    language = Column(String(10), nullable=False, index=True)
    previous_language = Column(String(10), nullable=True)
    event_type = Column(SQLEnum(EventTypeEnum, values_callable=lambda x: [e.value for e in x]), nullable=False, default=EventTypeEnum.CHANGE, server_default='change')
    created_at = Column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP", nullable=False, index=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
