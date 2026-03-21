"""
Schemas for language tracking and analytics
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class LanguagePreferenceUpdate(BaseModel):
    """Request to update user's language preference"""
    language: str = Field(..., min_length=2, max_length=10, description="Language code (e.g., 'en', 'hi')")
    previous_language: Optional[str] = Field(None, max_length=10, description="Previous language (if known)")


class LanguageEventCreate(BaseModel):
    """Request to log a language change event (anonymous or authenticated)"""
    session_id: str = Field(..., min_length=1, max_length=100, description="Session ID for tracking")
    language: str = Field(..., min_length=2, max_length=10, description="Selected language code")
    previous_language: Optional[str] = Field(None, max_length=10, description="Previous language (if known)")
    user_agent: Optional[str] = Field(None, description="Browser user agent")


class LanguageDistribution(BaseModel):
    """Language usage distribution data"""
    language: str
    user_count: int
    session_count: int
    event_count: int
    percentage: float
    
    class Config:
        from_attributes = True


class LanguageTrendPoint(BaseModel):
    """Single data point in language trend"""
    date: str  # ISO format date
    language: str
    event_count: int
    
    class Config:
        from_attributes = True


class LanguageStatsResponse(BaseModel):
    """Comprehensive language usage statistics"""
    total_events: int
    total_unique_users: int
    total_unique_sessions: int
    most_popular_language: str
    supported_languages: List[str]
    distribution: List[LanguageDistribution]
    trends: Optional[List[LanguageTrendPoint]] = None
    
    class Config:
        from_attributes = True


class LanguageEventResponse(BaseModel):
    """Response after logging a language event"""
    success: bool
    message: str
    event_id: Optional[int] = None
