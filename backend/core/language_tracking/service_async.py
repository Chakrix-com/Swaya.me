"""
Language Tracking Service - Analytics and event logging for language usage - Async Version
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, case, and_, select
from datetime import datetime, date
from typing import Optional, List
import logging

from persistence.models.core import User, LanguageUsageEvent, EventTypeEnum
from .schemas import (
    LanguageDistribution,
    LanguageTrendPoint,
    LanguageStatsResponse,
    LanguageEventResponse
)

logger = logging.getLogger(__name__)


class LanguageTrackingServiceAsync:
    """Async service for tracking and analyzing language usage patterns"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def update_user_language_preference(
        self,
        user_id: int,
        language: str
    ) -> bool:
        """
        Update user's language preference in their profile
        
        Args:
            user_id: ID of the user
            language: Language code (e.g., 'en', 'hi', 'es')
            
        Returns:
            True if update succeeded, False otherwise
        """
        try:
            result = await self.db.execute(
                select(User).filter(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"User {user_id} not found for language update")
                return False
            
            user.language_preference = language
            await self.db.commit()
            
            logger.info(f"Updated language preference for user {user_id} to {language}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user language preference: {e}")
            await self.db.rollback()
            return False
    
    async def log_language_event(
        self,
        user_id: Optional[int],
        session_id: str,
        language: str,
        previous_language: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        tenant_id: Optional[int] = None
    ) -> LanguageEventResponse:
        """
        Log a language selection or change event
        
        Args:
            user_id: ID of authenticated user (None for anonymous)
            session_id: Session identifier for tracking
            language: Selected language code
            previous_language: Previous language (if known)
            user_agent: Browser user agent string
            ip_address: User's IP address
            tenant_id: Tenant ID (if in multi-tenant context)
            
        Returns:
            LanguageEventResponse with success status and event ID
        """
        try:
            # Determine event type
            event_type = EventTypeEnum.INITIAL if previous_language is None else EventTypeEnum.CHANGE
            
            # Create event record
            event = LanguageUsageEvent(
                user_id=user_id,
                session_id=session_id,
                language=language,
                previous_language=previous_language,
                event_type=event_type,
                user_agent=user_agent,
                ip_address=ip_address,
                tenant_id=tenant_id
            )
            
            self.db.add(event)
            await self.db.commit()
            await self.db.refresh(event)
            
            logger.info(
                f"Logged {event_type.value} language event: "
                f"user_id={user_id}, session={session_id}, lang={language}"
            )
            
            return LanguageEventResponse(
                success=True,
                message=f"Language event logged successfully",
                event_id=event.id
            )
            
        except Exception as e:
            logger.error(f"Error logging language event: {e}")
            await self.db.rollback()
            return LanguageEventResponse(
                success=False,
                message=f"Failed to log language event: {str(e)}",
                event_id=None
            )
    
    async def get_language_distribution(self) -> List[LanguageDistribution]:
        """
        Get current language distribution from users table
        
        Returns:
            List of LanguageDistribution objects with user counts per language
        """
        try:
            # Query active users grouped by language preference
            stmt = select(
                User.language_preference.label('language'),
                func.count(User.id).label('user_count')
            ).filter(
                User.is_active == True
            ).group_by(
                User.language_preference
            )
            
            result = await self.db.execute(stmt)
            results = result.all()
            
            total_users = sum(row.user_count for row in results)
            
            distributions = []
            for row in results:
                percentage = (row.user_count / total_users * 100) if total_users > 0 else 0.0
                
                distributions.append(LanguageDistribution(
                    language=row.language,
                    user_count=row.user_count,
                    session_count=0,  # Not available from users table
                    event_count=0,    # Not available from users table
                    percentage=round(percentage, 2)
                ))
            
            return sorted(distributions, key=lambda x: x.user_count, reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting language distribution: {e}")
            return []
    
    async def get_language_event_stats(self) -> List[LanguageDistribution]:
        """
        Get language statistics from events table
        Includes unique users, unique sessions, and total events per language
        
        Returns:
            List of LanguageDistribution objects with detailed event stats
        """
        try:
            # Query events grouped by language with aggregations
            stmt = select(
                LanguageUsageEvent.language,
                func.count(func.distinct(LanguageUsageEvent.user_id)).label('user_count'),
                func.count(func.distinct(LanguageUsageEvent.session_id)).label('session_count'),
                func.count(LanguageUsageEvent.id).label('event_count')
            ).group_by(
                LanguageUsageEvent.language
            )
            
            result = await self.db.execute(stmt)
            results = result.all()
            
            total_events = sum(row.event_count for row in results)
            
            distributions = []
            for row in results:
                percentage = (row.event_count / total_events * 100) if total_events > 0 else 0.0
                
                distributions.append(LanguageDistribution(
                    language=row.language,
                    user_count=row.user_count or 0,
                    session_count=row.session_count or 0,
                    event_count=row.event_count,
                    percentage=round(percentage, 2)
                ))
            
            return sorted(distributions, key=lambda x: x.event_count, reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting language event stats: {e}")
            return []
    
    async def get_language_trends(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[LanguageTrendPoint]:
        """
        Get language usage trends over time
        Groups events by date and language
        
        Args:
            start_date: Start of date range (defaults to 30 days ago)
            end_date: End of date range (defaults to today)
            
        Returns:
            List of LanguageTrendPoint objects with daily event counts
        """
        try:
            # Set default date range if not provided
            if end_date is None:
                end_date = datetime.utcnow()
            if start_date is None:
                from datetime import timedelta
                start_date = end_date - timedelta(days=30)
            
            # Query events grouped by date and language
            stmt = select(
                func.date(LanguageUsageEvent.created_at).label('event_date'),
                LanguageUsageEvent.language,
                func.count(LanguageUsageEvent.id).label('event_count')
            ).filter(
                and_(
                    LanguageUsageEvent.created_at >= start_date,
                    LanguageUsageEvent.created_at <= end_date
                )
            ).group_by(
                func.date(LanguageUsageEvent.created_at),
                LanguageUsageEvent.language
            ).order_by(
                func.date(LanguageUsageEvent.created_at).asc()
            )
            
            result = await self.db.execute(stmt)
            results = result.all()
            
            trends = []
            for row in results:
                trends.append(LanguageTrendPoint(
                    date=row.event_date.isoformat() if isinstance(row.event_date, date) else str(row.event_date),
                    language=row.language,
                    event_count=row.event_count
                ))
            
            return trends
            
        except Exception as e:
            logger.error(f"Error getting language trends: {e}")
            return []
    
    async def get_language_stats_summary(
        self,
        include_trends: bool = False,
        trend_days: int = 30
    ) -> LanguageStatsResponse:
        """
        Get comprehensive language usage statistics for admin dashboard
        
        Args:
            include_trends: Whether to include trend data
            trend_days: Number of days of trend data to include
            
        Returns:
            LanguageStatsResponse with complete statistics
        """
        try:
            # Get overall statistics
            stmt = select(
                func.count(LanguageUsageEvent.id).label('total_events'),
                func.count(func.distinct(LanguageUsageEvent.user_id)).label('unique_users'),
                func.count(func.distinct(LanguageUsageEvent.session_id)).label('unique_sessions')
            )
            
            result = await self.db.execute(stmt)
            total_stats = result.first()
            
            # Get language distribution from events
            distributions = await self.get_language_event_stats()
            
            # Determine most popular language
            most_popular = distributions[0].language if distributions else 'en'
            
            # Get list of all languages seen
            supported_languages = [dist.language for dist in distributions]
            
            # Optionally get trend data
            trends = None
            if include_trends:
                from datetime import timedelta
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=trend_days)
                trends = await self.get_language_trends(start_date, end_date)
            
            return LanguageStatsResponse(
                total_events=total_stats.total_events or 0,
                total_unique_users=total_stats.unique_users or 0,
                total_unique_sessions=total_stats.unique_sessions or 0,
                most_popular_language=most_popular,
                supported_languages=supported_languages,
                distribution=distributions,
                trends=trends
            )
            
        except Exception as e:
            logger.error(f"Error getting language stats summary: {e}")
            # Return empty stats on error
            return LanguageStatsResponse(
                total_events=0,
                total_unique_users=0,
                total_unique_sessions=0,
                most_popular_language='en',
                supported_languages=[],
                distribution=[],
                trends=None
            )
