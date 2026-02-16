"""
Pydantic schemas for Quiz feature
"""
from pydantic import BaseModel, Field, validator, model_validator
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


class QuestionTypeEnum(str, Enum):
    """Question type"""
    MCQ = "mcq"
    WORD_CLOUD = "word_cloud"


# Question Schemas
class QuestionOptionCreate(BaseModel):
    """Question option"""
    text: str = Field(..., min_length=1, max_length=500)


class QuestionCreate(BaseModel):
    """Create question request"""
    question_type: QuestionTypeEnum = Field(default=QuestionTypeEnum.MCQ)
    text: str = Field(..., min_length=1, max_length=1000)
    options: Optional[List[str]] = None
    correct_answer_index: Optional[int] = Field(None, ge=0, le=3)
    
    @model_validator(mode='after')
    def validate_question_fields(self):
        """Validate fields based on question type"""
        if self.question_type == QuestionTypeEnum.MCQ:
            # MCQ must have options and correct answer
            if not self.options or len(self.options) != 4:
                raise ValueError('MCQ questions must have exactly 4 options')
            if any(not opt.strip() for opt in self.options):
                raise ValueError('All options must be non-empty')
            if self.correct_answer_index is None:
                raise ValueError('MCQ questions must have a correct answer')
        elif self.question_type == QuestionTypeEnum.WORD_CLOUD:
            # Word cloud must NOT have options or correct answer
            if self.options is not None:
                raise ValueError('Word cloud questions should not have options')
            if self.correct_answer_index is not None:
                raise ValueError('Word cloud questions should not have a correct answer')
        return self


class QuestionUpdate(BaseModel):
    """Update question request"""
    question_type: Optional[QuestionTypeEnum] = None
    text: Optional[str] = Field(None, min_length=1, max_length=1000)
    options: Optional[List[str]] = Field(None, min_items=4, max_items=4)
    correct_answer_index: Optional[int] = Field(None, ge=0, le=3)


class QuestionResponse(BaseModel):
    """Question response"""
    id: int
    question_type: QuestionTypeEnum
    text: str
    options: Optional[List[str]] = None
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
    """Submit answer request for MCQ"""
    question_id: int
    selected_option_index: int = Field(..., ge=0, le=3)


class WordCloudAnswerSubmitRequest(BaseModel):
    """Submit answer request for word cloud"""
    question_id: int
    text_answer: str = Field(..., min_length=1, max_length=100)


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


class WordCloudResultsResponse(BaseModel):
    """Word cloud question results"""
    question_id: int
    question_text: str
    word_frequencies: dict[str, int]  # {word: count}
    total_submissions: int
    unique_words: int
