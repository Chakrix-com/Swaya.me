"""
Statistics snapshot model for historical tracking
"""
from sqlalchemy import Column, Integer, DateTime, Enum as SQLEnum, ForeignKey, JSON
import enum

from persistence.database import Base
from persistence.models.base import TimestampMixin


class SnapshotGranularity(str, enum.Enum):
    """Snapshot granularity types"""
    HOURLY = "HOURLY"
    DAILY = "DAILY"


class SnapshotScope(str, enum.Enum):
    """Snapshot scope types"""
    PLATFORM = "PLATFORM"
    TENANT = "TENANT"


class StatsSnapshot(Base, TimestampMixin):
    """Historical statistics snapshot"""
    __tablename__ = "stats_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    captured_at = Column(DateTime, nullable=False, index=True)
    granularity = Column(SQLEnum(SnapshotGranularity), nullable=False, index=True)
    scope = Column(SQLEnum(SnapshotScope), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    stats_data = Column(JSON, nullable=False)
