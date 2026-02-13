"""
Pydantic schemas for Quiz feature
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from enum import Enum


class QuizStatusEnum(str, Enum):
    """Quiz status"""
    DRAFT = "draft"
    READY = "ready"
    ARCHIVED = "archived"


class SessionStatusEnum(str, Enum):
    """Session status"""
    CREATED = "created"
    ACTIVE = "active"
    ENDED = "ended"


class QuestionStatusEnum(str, Enum):
    """Question status during session"""
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"


# Question Schemas
class QuestionOptionCreate(BaseModel):
    """Question option"""
    text: str = Field(..., min_length=1, max_length=500)


class QuestionCreate(BaseModel):
    """Create question request"""
    text: str = Field(..., min_length=1, max_length=1000)
    options: List[str] = Field(..., min_items=4, max_items=4)
    correct_answer_index: int = Field(..., ge=0, le=3)
    
    @validator('options')
    def validate_options(cls, v):
        """Ensure all options are non-empty"""
        if any(not opt.strip() for opt in v):
            raise ValueError('All options must be non-empty')
        return v


class QuestionUpdate(BaseModel):
    """Update question request"""
    text: Optional[str] = Field(None, min_length=1, max_length=1000)
    options: Optional[List[str]] = Field(None, min_items=4, max_items=4)
    correct_answer_index: Optional[int] = Field(None, ge=0, le=3)


class QuestionResponse(BaseModel):
    """Question response"""
    id: int
    text: str
    options: List[str]
    order: int
    correct_answer_index: Optional[int] = None  # Hidden during active session
    
    class Config:
        from_attributes = True


class QuestionReorderRequest(BaseModel):
    """Reorder questions request"""
    question_orders: List[tuple[int, int]] = Field(..., description="List of (question_id, new_order)")


# Quiz Schemas
class QuizCreate(BaseModel):
    """Create quiz request"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    event_id: Optional[int] = Field(None, description="Event ID (auto-created if not provided)")


class QuizUpdate(BaseModel):
    """Update quiz request"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)


class QuizResponse(BaseModel):
    """Quiz response"""
    id: int
    event_id: int
    title: str
    description: Optional[str]
    status: QuizStatusEnum
    questions: List[QuestionResponse] = []
    question_count: int = 0
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class QuizListResponse(BaseModel):
    """Quiz list response"""
    id: int
    event_id: int
    title: str
    status: QuizStatusEnum
    question_count: int
    created_at: str
    
    class Config:
        from_attributes = True


# Session Schemas
class SessionStartRequest(BaseModel):
    """Start quiz session request"""
    quiz_id: int


class SessionResponse(BaseModel):
    """Session response"""
    id: int
    quiz_id: int
    quiz_title: str
    status: SessionStatusEnum
    current_question_index: int
    current_question_status: Optional[QuestionStatusEnum]
    join_code: str
    participant_count: int = 0
    
    class Config:
        from_attributes = True


class SessionJoinRequest(BaseModel):
    """Join session request"""
    join_code: str
    display_name: Optional[str] = Field(None, max_length=100)


class SessionJoinResponse(BaseModel):
    """Join session response"""
    session_id: int
    session_token: str
    participant_id: int
    quiz_title: str
    status: SessionStatusEnum


# Answer Schemas
class AnswerSubmitRequest(BaseModel):
    """Submit answer request"""
    question_id: int
    selected_option_index: int = Field(..., ge=0, le=3)


class AnswerSubmitResponse(BaseModel):
    """Answer submit response"""
    success: bool
    message: str
    is_correct: Optional[bool] = None  # Only revealed after question closes


class QuestionResultsResponse(BaseModel):
    """Question results after closing"""
    question_id: int
    question_text: str
    options: List[str]
    correct_answer_index: int
    answer_distribution: List[int]  # Count per option
    total_answers: int
    participant_answer: Optional[int] = None  # What this participant answered


class SessionResultsResponse(BaseModel):
    """Final session results"""
    session_id: int
    quiz_title: str
    total_questions: int
    total_participants: int = 0
    participant_score: Optional[int] = None
    participant_correct: Optional[int] = None
    question_results: List[QuestionResultsResponse]
    # Session state for audience
    status: str
    current_question_index: int
    current_question: Optional[dict] = None  # Mixed format for host view
