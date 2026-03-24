"""
App-level feedback model (not quiz-scoped)
"""
from sqlalchemy import Column, Integer, String, Text

from persistence.database import Base
from persistence.models.base import TimestampMixin


class AppFeedback(Base, TimestampMixin):
    """Feedback submitted via the global floating button from any page."""

    __tablename__ = "app_feedback"

    id = Column(Integer, primary_key=True, index=True)
    page_url = Column(String(500), nullable=False)
    feedback_text = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)          # 1–5, optional
    source_type = Column(String(20), nullable=False)  # "anonymous" | "user"
    user_id = Column(Integer, nullable=True, index=True)   # plain int, no FK
    tenant_id = Column(Integer, nullable=True, index=True)
    display_name = Column(String(100), nullable=True)
    user_email = Column(String(255), nullable=True)
    user_agent = Column(String(500), nullable=True)
