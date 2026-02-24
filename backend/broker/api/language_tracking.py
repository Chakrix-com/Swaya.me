"""
API endpoints for language tracking and analytics
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import logging

from persistence.database import get_db
from core.auth.dependencies import get_current_user, CurrentUser
from core.language_tracking.service import LanguageTrackingService
from core.language_tracking.schemas import (
    LanguagePreferenceUpdate,
    LanguageEventCreate,
    LanguageStatsResponse,
    LanguageEventResponse
)
from persistence.models.core import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(tags=["language-tracking"])


@router.post("/user/language-preference", response_model=LanguageEventResponse)
async def update_language_preference(
    request_data: LanguagePreferenceUpdate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update authenticated user's language preference and log event
    """
    try:
        service = LanguageTrackingService(db)
        
        # Update user preference
        service.update_user_language_preference(current_user.user_id, request_data.language)
        
        # Log the event
        user_agent = request.headers.get("user-agent")
        ip_address = request.client.host if request.client else None
        session_id = request.headers.get("x-session-id", f"user_{current_user.user_id}")
        
        result = service.log_language_event(
            user_id=current_user.user_id,
            session_id=session_id,
            language=request_data.language,
            previous_language=request_data.previous_language,
            user_agent=user_agent,
            ip_address=ip_address,
            tenant_id=current_user.tenant_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to update language preference: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update language preference")


@router.post("/language-tracking/event", response_model=LanguageEventResponse)
async def log_language_event(
    request_data: LanguageEventCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Log a language change event (for anonymous users)
    No authentication required
    """
    try:
        service = LanguageTrackingService(db)
        
        # Get IP address from request
        ip_address = request.client.host if request.client else None
        
        # Log the event (no user_id for anonymous)
        result = service.log_language_event(
            user_id=None,
            session_id=request_data.session_id,
            language=request_data.language,
            previous_language=request_data.previous_language,
            user_agent=request_data.user_agent,
            ip_address=ip_address,
            tenant_id=None  # Anonymous users not tied to tenant
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to log language event: {str(e)}")
        # Don't fail the request for anonymous tracking
        return LanguageEventResponse(
            success=False,
            message="Event logging failed (non-critical)",
            event_id=None
        )


@router.get("/admin/language-stats")
async def get_language_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive language usage statistics
    Admin-only endpoint
    """
    # Check if user is admin or super_admin
    if current_user.user.role not in [UserRole.admin, UserRole.super_admin]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        service = LanguageTrackingService(db)
        
        # Parse date range if provided
        start = None
        end = None
        if start_date:
            try:
                start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format")
        
        if end_date:
            try:
                end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format")
        
        # Get comprehensive stats (ignore date filters for now, use trend_days)
        stats = service.get_language_stats_summary(
            include_trends=True,
            trend_days=30
        )
        
        # Transform to frontend-expected format
        response = {
            "distribution": [
                {"language": d.language, "count": d.event_count}
                for d in stats.distribution
            ],
            "event_stats": [
                {
                    "language": d.language,
                    "total_events": d.event_count,
                    "unique_users": d.user_count,
                    "unique_sessions": d.session_count
                }
                for d in stats.distribution
            ],
            "trends": [
                {"date": t.date, "language": t.language, "count": t.event_count}
                for t in (stats.trends or [])
            ],
            "summary": {
                "total_events": stats.total_events,
                "unique_users": stats.total_unique_users,
                "unique_sessions": stats.total_unique_sessions,
                "most_popular_language": stats.most_popular_language,
                "most_popular_count": stats.distribution[0].event_count if stats.distribution else 0
            }
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get language stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve language statistics")


@router.get("/admin/language-stats/export")
async def export_language_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export language usage data as CSV
    Admin-only endpoint
    """
    # Check if user is admin or super_admin
    if current_user.user.role not in [UserRole.admin, UserRole.super_admin]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        from fastapi.responses import StreamingResponse
        import io
        import csv
        
        service = LanguageTrackingService(db)
        
        # Parse dates
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00')) if start_date else None
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00')) if end_date else None
        
        # Get trends data
        trends = service.get_language_trends(start_date=start, end_date=end)
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['Date', 'Language', 'Event Count'])
        
        # Write data
        for trend in trends:
            writer.writerow([trend.date, trend.language, trend.event_count])
        
        # Prepare response
        output.seek(0)
        filename = f"language_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Failed to export language stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to export language statistics")
