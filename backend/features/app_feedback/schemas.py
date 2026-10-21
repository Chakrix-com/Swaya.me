"""
Schemas for global app feedback
"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, validator, Field, computed_field
from shared.utils.html_sanitizer import sanitize_plain


class AppFeedbackSubmitRequest(BaseModel):
    page_url: str = Field(..., max_length=500)
    feedback_text: str = Field(..., min_length=2, max_length=10000)
    rating: Optional[int] = Field(None, ge=1, le=5)
    display_name: Optional[str] = Field(None, max_length=100)

    @validator('feedback_text')
    def sanitize_feedback(cls, v):
        # Strip all HTML — feedback is plain text, rendered via dangerouslySetInnerHTML
        return sanitize_plain(v)


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
    attachments: Optional[List[str]] = None

    @computed_field
    @property
    def attachment_urls(self) -> List[str]:
        # Served by the super-admin-only route in broker/api/app_feedback.py
        return [f"/api/v1/admin/app-feedback/{self.id}/attachments/{name}" for name in (self.attachments or [])]

    class Config:
        from_attributes = True


class AppFeedbackListResponse(BaseModel):
    items: List[AppFeedbackResponse]
    total: int
    limit: int
    offset: int
