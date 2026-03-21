"""
Pydantic schemas for Quiz feature
"""
from pydantic import BaseModel, Field, validator, model_validator
from typing import List, Optional
from datetime import datetime
from enum import Enum


class QuizStatusEnum(str, Enum):
    """Quiz status"""
    DRAFT = "draft"
    READY = "ready"
    ARCHIVED = "archived"


class QuizTypeEnum(str, Enum):
    """Quiz experience type"""
    QUIZ = "quiz"
    POLL = "poll"


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
    SINGLE_LINE = "single_line"
    SCALE = "scale"
    PARAGRAPH = "paragraph"


class TemplateScopeEnum(str, Enum):
    """Template visibility scope"""
    TENANT = "tenant"
    GLOBAL = "global"


# Question Schemas
class QuestionOptionCreate(BaseModel):
    """Question option"""
    text: str = Field(..., min_length=1, max_length=500)


class QuestionCreate(BaseModel):
    """Create question request"""
    question_type: QuestionTypeEnum = Field(default=QuestionTypeEnum.MCQ)
    text: str = Field(..., min_length=1, max_length=1000)
    options: Optional[List[str]] = None
    correct_answer_index: Optional[int] = Field(None, ge=0)
    question_image_url: Optional[str] = Field(None, max_length=500)
    option_images: Optional[dict[str, str]] = None  # {"A": "path", "B": "path", ...}
    points: int = Field(default=1, ge=1)
    max_time_seconds: Optional[int] = Field(default=None, ge=1, le=3600)
    
    @model_validator(mode='after')
    def validate_question_fields(self):
        """Validate fields based on question type"""
        if self.question_type == QuestionTypeEnum.MCQ:
            # MCQ must have options and correct answer
            if not self.options or len(self.options) < 2:
                raise ValueError('MCQ questions must have at least 2 options')
            if len(self.options) > 10:
                raise ValueError('MCQ questions can have at most 10 options')
            if any(not opt.strip() for opt in self.options):
                raise ValueError('All options must be non-empty')
            if self.correct_answer_index is not None and not (0 <= self.correct_answer_index < len(self.options)):
                raise ValueError('MCQ correct answer index must reference an existing option')
        elif self.question_type == QuestionTypeEnum.WORD_CLOUD:
            # Word cloud must NOT have options or correct answer
            if self.options is not None:
                raise ValueError('Word cloud questions should not have options')
            if self.correct_answer_index is not None:
                raise ValueError('Word cloud questions should not have a correct answer')
        elif self.question_type == QuestionTypeEnum.SINGLE_LINE:
            if self.options is not None and len(self.options) > 1:
                raise ValueError('Single-line questions can have at most one expected answer')
            if self.correct_answer_index is not None:
                raise ValueError('Single-line questions should not have a correct answer')
        elif self.question_type == QuestionTypeEnum.PARAGRAPH:
            if self.options is not None and len(self.options) > 1:
                raise ValueError('Paragraph questions can have at most one expected answer')
            if self.correct_answer_index is not None:
                raise ValueError('Paragraph questions should not have a correct answer')
        elif self.question_type == QuestionTypeEnum.SCALE:
            if not self.options or len(self.options) != 5:
                raise ValueError('Scale questions must have exactly 5 options')
            if self.correct_answer_index is not None and (self.correct_answer_index < 0 or self.correct_answer_index > 4):
                raise ValueError('Scale correct answer must be between 1 and 5')
        return self


class QuestionUpdate(BaseModel):
    """Update question request"""
    question_type: Optional[QuestionTypeEnum] = None
    text: Optional[str] = Field(None, min_length=1, max_length=1000)
    options: Optional[List[str]] = None
    correct_answer_index: Optional[int] = Field(None, ge=0)
    question_image_url: Optional[str] = Field(None, max_length=500)
    option_images: Optional[dict[str, str]] = None
    points: Optional[int] = Field(default=None, ge=1)
    max_time_seconds: Optional[int] = Field(default=None, ge=1, le=3600)


class QuestionResponse(BaseModel):
    """Question response"""
    id: int
    question_type: QuestionTypeEnum
    text: str
    options: Optional[List[str]] = None
    order: int
    correct_answer_index: Optional[int] = None  # Hidden during active session
    question_image_url: Optional[str] = None
    option_images: Optional[dict[str, str]] = None
    points: int = 1
    max_time_seconds: Optional[int] = None
    
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
    quiz_type: QuizTypeEnum = QuizTypeEnum.QUIZ


class QuizUpdate(BaseModel):
    """Update quiz request"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    quiz_type: Optional[QuizTypeEnum] = None


class QuizResponse(BaseModel):
    """Quiz response"""
    id: int
    event_id: int
    title: str
    description: Optional[str]
    quiz_type: QuizTypeEnum = QuizTypeEnum.QUIZ
    status: QuizStatusEnum
    folder_id: Optional[int] = None
    folder_path: Optional[str] = None
    is_template: bool = False
    template_scope: TemplateScopeEnum = TemplateScopeEnum.TENANT
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
    quiz_type: QuizTypeEnum = QuizTypeEnum.QUIZ
    status: QuizStatusEnum
    folder_id: Optional[int] = None
    folder_path: Optional[str] = None
    is_template: bool = False
    template_scope: TemplateScopeEnum = TemplateScopeEnum.TENANT
    question_count: int
    has_active_session: bool = False
    active_session_id: Optional[int] = None
    created_at: str
    
    class Config:
        from_attributes = True


# Session Schemas
class SessionStartRequest(BaseModel):
    """Start quiz session request"""
    quiz_id: int


class FolderCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: Optional[int] = None


class FolderUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    parent_id: Optional[int] = None


class FolderAssignRequest(BaseModel):
    folder_id: Optional[int] = None


class FolderResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    sort_order: int = 0
    path: str
    children: List["FolderResponse"] = []


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

class SessionLeaveResponse(BaseModel):
    """Leave session response"""
    success: bool
    message: str


class WhiteboardStateUpdateRequest(BaseModel):
    """Persist presenter whiteboard state for current question"""
    question_index: int = Field(..., ge=-1)
    enabled: bool = False
    image_data: Optional[str] = None


class WhiteboardStateResponse(BaseModel):
    """Whiteboard state for present screen"""
    session_id: int
    question_index: int
    enabled: bool
    image_data: Optional[str] = None
    updated_at: Optional[str] = None


# Answer Schemas
class AnswerSubmitRequest(BaseModel):
    """Submit answer request for MCQ"""
    question_id: int
    selected_option_index: int = Field(..., ge=0)


class WordCloudAnswerSubmitRequest(BaseModel):
    """Submit answer request for word cloud"""
    question_id: int
    text_answer: str = Field(..., min_length=1, max_length=2000)


class AnswerSubmitResponse(BaseModel):
    """Answer submit response"""
    success: bool
    message: str
    is_correct: Optional[bool] = None  # Only revealed after question closes


class QuestionResultsResponse(BaseModel):
    """Question results after closing"""
    question_id: int
    question_text: str
    options: Optional[List[str]] = None
    correct_answer_index: Optional[int] = None
    answer_distribution: List[int]  # Count per option
    total_answers: int
    participant_answer: Optional[int] = None  # What this participant answered


class SessionResultsResponse(BaseModel):
    """Final session results"""
    session_id: int
    quiz_title: str
    quiz_type: QuizTypeEnum = QuizTypeEnum.QUIZ
    scoring_enabled: bool = True
    total_questions: int
    total_participants: int = 0
    participant_score: Optional[int] = None
    participant_correct: Optional[int] = None
    question_results: List[QuestionResultsResponse]
    # Session state for audience
    status: str
    current_question_index: int
    current_question: Optional[dict] = None  # Mixed format for host view
    leaderboard_visible: bool = True


class WordCloudResultsResponse(BaseModel):
    """Word cloud question results"""
    question_id: int
    question_text: str
    word_frequencies: dict[str, int]  # {word: count}
    total_submissions: int
    unique_words: int


class FeedbackSubmitRequest(BaseModel):
    """Submit feedback request"""
    feedback_text: str = Field(..., min_length=2, max_length=2000)
    rating: Optional[int] = Field(None, ge=1, le=5)
    quiz_id: Optional[int] = None
    session_id: Optional[int] = None
    display_name: Optional[str] = Field(None, max_length=100)


class FeedbackResponse(BaseModel):
    """Feedback response payload"""
    id: int
    quiz_id: int
    quiz_title: str
    tenant_id: int
    session_id: Optional[int] = None
    participant_id: Optional[int] = None
    user_id: Optional[int] = None
    source_type: str
    display_name: Optional[str] = None
    user_email: Optional[str] = None
    rating: Optional[int] = None
    feedback_text: str
    created_at: datetime


class FeedbackListResponse(BaseModel):
    """Paginated feedback list response"""
    items: List[FeedbackResponse]
    total: int
    limit: int
    offset: int


class SessionListItemResponse(BaseModel):
    """Summary of a single past session"""
    id: int
    status: SessionStatusEnum
    created_at: datetime
    ended_at: Optional[datetime] = None
    participant_count: int
    total_responses: int


class SessionListResponse(BaseModel):
    """List of sessions for a quiz"""
    quiz_id: int
    quiz_title: str
    sessions: list
    total: int


class LeaderboardEntry(BaseModel):
    """Single leaderboard entry"""
    rank: int
    participant_id: int
    display_name: str
    score: int  # weighted score based on question points
    is_current_participant: bool = False
    time_taken_seconds: Optional[float] = None  # Time from join to last correct answer


class LeaderboardResponse(BaseModel):
    """Leaderboard for a session"""
    session_id: int
    entries: List[LeaderboardEntry]
    total_participants: int
    current_participant_rank: Optional[int] = None
    mcq_question_count: int = 0


class PlatformQuizListItemResponse(BaseModel):
    """Platform-wide quiz list item for super admin"""
    id: int
    event_id: int
    tenant_id: int
    tenant_name: str
    title: str
    status: QuizStatusEnum
    is_template: bool = False
    template_scope: TemplateScopeEnum = TemplateScopeEnum.TENANT
    question_count: int
    created_at: datetime
    updated_at: datetime


class PlatformQuizListResponse(BaseModel):
    """Paginated platform quiz list response"""
    items: List[PlatformQuizListItemResponse]
    total: int
    limit: int
    offset: int


class TemplateDesignationRequest(BaseModel):
    """Mark or unmark a quiz as template"""
    is_template: bool


class TemplateQuizListItemResponse(BaseModel):
    """Template quiz visible to a user"""
    id: int
    title: str
    description: Optional[str] = None
    quiz_type: QuizTypeEnum = QuizTypeEnum.QUIZ
    status: QuizStatusEnum
    question_count: int
    template_scope: TemplateScopeEnum
    tenant_id: int
    created_at: datetime


FolderResponse.model_rebuild()
