from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timedelta
from typing import Optional

from persistence.models.core import User, Tenant
from persistence.models.quiz import Quiz, QuizSession, QuizSessionStatus
from .schemas import (
    StatsResponse, StatsData, UserStats, QuizStats,
    SessionStats, ParticipantStats, LoadStats
)


class StatsService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_platform_stats(self) -> StatsResponse:
        """Get platform-wide statistics (all tenants)"""
        return StatsResponse(
            scope="platform",
            stats=StatsData(
                users=self._get_user_stats(),
                quizzes=self._get_quiz_stats(),
                sessions=self._get_session_stats(),
                participants=self._get_participant_stats(),
                load=self._get_load_stats()
            ),
            timestamp=datetime.utcnow()
        )
    
    def get_tenant_stats(self, tenant_id: int) -> StatsResponse:
        """Get tenant-specific statistics"""
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        
        return StatsResponse(
            scope="tenant",
            tenant_id=tenant_id,
            tenant_name=tenant.name if tenant else None,
            stats=StatsData(
                users=self._get_user_stats(tenant_id),
                quizzes=self._get_quiz_stats(tenant_id),
                sessions=self._get_session_stats(tenant_id),
                participants=self._get_participant_stats(tenant_id),
                load=None
            ),
            timestamp=datetime.utcnow()
        )
    
    def _get_user_stats(self, tenant_id: Optional[int] = None) -> UserStats:
        query = self.db.query(
            func.count(User.id).label('total'),
            func.sum(case((User.is_active == True, 1), else_=0)).label('active'),
            func.sum(case((User.is_active == False, 1), else_=0)).label('inactive')
        )
        
        if tenant_id:
            query = query.filter(User.tenant_id == tenant_id)
        
        result = query.first()
        
        return UserStats(
            total=result.total or 0,
            active=result.active or 0,
            inactive=result.inactive or 0
        )
    
    def _get_quiz_stats(self, tenant_id: Optional[int] = None) -> QuizStats:
        query = self.db.query(
            Quiz.status,
            func.count(Quiz.id).label('count')
        )
        
        if tenant_id:
            query = query.filter(Quiz.tenant_id == tenant_id)
        
        results = query.group_by(Quiz.status).all()
        
        # Use .value to get the actual enum value ('draft', 'ready', etc.)
        status_counts = {row.status.value: row.count for row in results}
        
        return QuizStats(
            total=sum(status_counts.values()),
            ready=status_counts.get('ready', 0),
            draft=status_counts.get('draft', 0),
            archived=status_counts.get('archived', 0)
        )
    
    def _get_session_stats(self, tenant_id: Optional[int] = None) -> SessionStats:
        base_query = self.db.query(QuizSession)
        
        if tenant_id:
            base_query = base_query.filter(QuizSession.tenant_id == tenant_id)
        
        # Use QuizSessionStatus enum instead of string
        active = base_query.filter(QuizSession.status == QuizSessionStatus.ACTIVE).count()
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today = base_query.filter(QuizSession.created_at >= today_start).count()
        
        total = base_query.count()
        
        return SessionStats(
            active=active,
            total_today=today,
            total_all_time=total
        )
    
    def _get_participant_stats(self, tenant_id: Optional[int] = None) -> ParticipantStats:
        # For now, return zero counts as Participant model may not be fully implemented
        # This can be enhanced when participant tracking is added
        return ParticipantStats(
            total_all_time=0,
            active_now=0
        )
    
    def _get_load_stats(self) -> LoadStats:
        """Get system load metrics (super_admin only)"""
        try:
            import psutil
            from sqlalchemy import text
            
            # Use interval=None for non-blocking call
            # Returns average since last call (or system boot on first call)
            cpu_percent = round(psutil.cpu_percent(interval=None), 1)
            
            # If first call returns 0, try once with a short interval
            if cpu_percent == 0.0:
                cpu_percent = round(psutil.cpu_percent(interval=0.1), 1)
            
            memory_percent = round(psutil.virtual_memory().percent, 1)
            
            # Try to get DB connection count
            try:
                db_connections = len(
                    self.db.execute(text("SHOW PROCESSLIST")).fetchall()
                )
            except Exception as e:
                # Log error but continue
                print(f"Warning: Failed to get DB connections: {e}")
                db_connections = 0
            
            return LoadStats(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                db_connections=db_connections
            )
        except ImportError:
            # psutil not installed, return default values
            return LoadStats(
                cpu_percent=0.0,
                memory_percent=0.0,
                db_connections=0
            )
        except Exception as e:
            # Any other error, return default values
            return LoadStats(
                cpu_percent=0.0,
                memory_percent=0.0,
                db_connections=0
            )
