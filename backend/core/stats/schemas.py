from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from persistence.models.stats import SnapshotGranularity, SnapshotScope


class UserStats(BaseModel):
    total: int
    active: int
    inactive: int


class QuizStats(BaseModel):
    total: int
    ready: int
    draft: int
    archived: int


class SessionStats(BaseModel):
    active: int
    total_today: int
    total_all_time: int


class ParticipantStats(BaseModel):
    total_all_time: int
    active_now: int


class LoadStats(BaseModel):
    cpu_percent: float
    memory_percent: float
    db_connections: int


class StatsData(BaseModel):
    users: UserStats
    quizzes: QuizStats
    sessions: SessionStats
    participants: ParticipantStats
    load: Optional[LoadStats] = None


class StatsResponse(BaseModel):
    scope: str
    tenant_id: Optional[int] = None
    tenant_name: Optional[str] = None
    stats: StatsData
    timestamp: datetime


class PlatformStats(BaseModel):
    """Alias for platform-wide stats"""
    pass


class TenantStats(BaseModel):
    """Alias for tenant-specific stats"""
    pass


class StatsHistoryResponse(BaseModel):
    """Response model for historical statistics snapshot"""
    captured_at: datetime
    granularity: SnapshotGranularity
    scope: SnapshotScope
    tenant_id: Optional[int] = None
    stats: Dict[str, Any]  # stats_data JSON
    
    class Config:
        from_attributes = True
