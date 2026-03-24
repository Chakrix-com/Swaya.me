"""
Schemas for global app feedback
"""
import re
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, validator, Field


def _sanitize_html(html: str) -> str:
    """Strip dangerous HTML constructs (XSS guard)."""
    if not html:
        return html
    # Remove script and iframe tags (with content)
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r'<iframe[^>]*>.*?</iframe>', '', html, flags=re.IGNORECASE | re.DOTALL)
    # Remove inline event handlers
    html = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    html = re.sub(r'\s+on\w+\s*=\s*[^\s>]+', '', html, flags=re.IGNORECASE)
    # Remove javascript: hrefs
    html = re.sub(r'href\s*=\s*["\']?\s*javascript:[^"\'>\s]*["\']?', 'href="#"', html, flags=re.IGNORECASE)
    return html


class AppFeedbackSubmitRequest(BaseModel):
    page_url: str = Field(..., max_length=500)
    feedback_text: str = Field(..., min_length=2, max_length=10000)
    rating: Optional[int] = Field(None, ge=1, le=5)
    display_name: Optional[str] = Field(None, max_length=100)

    @validator('feedback_text')
    def sanitize_feedback(cls, v):
        return _sanitize_html(v)


class AppFeedbackResponse(BaseModel):
    id: int
    page_url: str
    feedback_text: str
    rating: Optional[int]
    source_type: str
    user_id: Optional[int]
    tenant_id: Optional[int]
    display_name: Optional[str]
    user_email: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AppFeedbackListResponse(BaseModel):
    items: List[AppFeedbackResponse]
    total: int
    limit: int
    offset: int
