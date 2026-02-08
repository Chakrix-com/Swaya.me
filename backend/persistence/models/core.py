"""
Core domain models for multi-tenant architecture
"""
from sqlalchemy import Column, Integer, String, Boolean, Enum as SQLEnum, ForeignKey, Text
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
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    events = relationship("Event", back_populates="creator")


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
