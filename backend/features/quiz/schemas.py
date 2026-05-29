"""
Pydantic schemas for Quiz feature
"""
from pydantic import BaseModel, Field, EmailStr, validator, model_validator
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
    OFFLINE_POLL = "offline_poll"
    EXAM = "exam"


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
    ONE_WORD = "one_word"


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
    text: str = Field(..., min_length=1, max_length=10000)
    options: Optional[List[str]] = None
    correct_answer_index: Optional[int] = Field(None, ge=0)
    question_image_url: Optional[str] = Field(None, max_length=500)
    option_images: Optional[dict[str, str]] = None  # {"A": "path", "B": "path", ...}
    points: int = Field(default=1, ge=1)
    max_time_seconds: Optional[int] = Field(default=None, ge=1, le=3600)
    negative_points: int = Field(default=0, ge=0)
    is_required: bool = Field(default=False)
    answer_explanation: Optional[str] = Field(None, max_length=5000)

    @validator('text')
    def no_dangerous_html(cls, v):
        import re
        if re.search(r'<script|<iframe|on\w+\s*=', v, re.IGNORECASE):
            raise ValueError('Question text contains disallowed HTML')
        return v

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
        elif self.question_type == QuestionTypeEnum.ONE_WORD:
            if self.options is not None:
                raise ValueError('One-word questions should not have options')
            if self.correct_answer_index is not None:
                raise ValueError('One-word questions should not have a correct answer')
        return self


class QuestionUpdate(BaseModel):
    """Update question request"""
    question_type: Optional[QuestionTypeEnum] = None
    text: Optional[str] = Field(None, min_length=1, max_length=10000)
    options: Optional[List[str]] = None
    correct_answer_index: Optional[int] = Field(None, ge=0)
    question_image_url: Optional[str] = Field(None, max_length=500)
    option_images: Optional[dict[str, str]] = None
    points: Optional[int] = Field(default=None, ge=1)
    max_time_seconds: Optional[int] = Field(default=None, ge=1, le=3600)
    negative_points: Optional[int] = Field(default=None, ge=0)
    is_required: Optional[bool] = None
    answer_explanation: Optional[str] = Field(None, max_length=5000)


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
    negative_points: int = 0
    is_required: bool = False
    answer_explanation: Optional[str] = None

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
    # Offline poll fields
    offline_start_at: Optional[datetime] = None
    offline_end_at: Optional[datetime] = None
    offline_results_email: Optional[str] = Field(None, max_length=255)
    # Exam fields
    exam_start_at: Optional[datetime] = None
    exam_end_at: Optional[datetime] = None
    exam_time_limit_seconds: Optional[int] = Field(None, ge=60)
    exam_results_email: Optional[str] = Field(None, max_length=255)
    exam_require_email: Optional[bool] = None
    exam_allowed_domains: Optional[str] = None
    # Proctoring
    proctoring_policy: Optional[dict] = None

    @model_validator(mode='after')
    def validate_offline_poll_fields(self):
        if self.quiz_type == QuizTypeEnum.OFFLINE_POLL:
            if self.offline_start_at and self.offline_end_at:
                if self.offline_end_at <= self.offline_start_at:
                    raise ValueError('End date must be after start date')
        if self.quiz_type == QuizTypeEnum.EXAM:
            if self.exam_start_at and self.exam_end_at:
                if self.exam_end_at <= self.exam_start_at:
                    raise ValueError('Exam end date must be after start date')
        return self


class QuizUpdate(BaseModel):
    """Update quiz request"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    quiz_type: Optional[QuizTypeEnum] = None
    # Offline poll fields
    offline_start_at: Optional[datetime] = None
    offline_end_at: Optional[datetime] = None
    offline_results_email: Optional[str] = Field(None, max_length=255)
    # Exam fields
    exam_start_at: Optional[datetime] = None
    exam_end_at: Optional[datetime] = None
    exam_time_limit_seconds: Optional[int] = Field(None, ge=60)
    exam_results_email: Optional[str] = Field(None, max_length=255)
    exam_require_email: Optional[bool] = None
    exam_allowed_domains: Optional[str] = None
    # Proctoring
    proctoring_policy: Optional[dict] = None


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
    # Offline poll fields
    poll_slug: Optional[str] = None
    poll_url: Optional[str] = None
    offline_start_at: Optional[datetime] = None
    offline_end_at: Optional[datetime] = None
    offline_results_email: Optional[str] = None
    # Exam fields
    exam_slug: Optional[str] = None
    exam_url: Optional[str] = None
    exam_start_at: Optional[datetime] = None
    exam_end_at: Optional[datetime] = None
    exam_time_limit_seconds: Optional[int] = None
    exam_results_email: Optional[str] = None
    exam_require_email: bool = False
    exam_allowed_domains: Optional[str] = None
    has_previous_session: bool = False
    # Proctoring
    proctoring_policy: Optional[dict] = None

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
    response_count: int = 0
    has_active_session: bool = False
    active_session_id: Optional[int] = None
    created_at: str
    # Offline poll fields
    poll_slug: Optional[str] = None
    poll_url: Optional[str] = None
    offline_start_at: Optional[datetime] = None
    offline_end_at: Optional[datetime] = None
    # Exam fields
    exam_slug: Optional[str] = None
    exam_url: Optional[str] = None
    exam_start_at: Optional[datetime] = None
    exam_end_at: Optional[datetime] = None

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


# Offline Poll Schemas
class OfflinePollInfoResponse(BaseModel):
    """Public info about an offline poll (no auth required)"""
    quiz_id: Optional[int] = None
    slug: str
    title: str
    description: Optional[str] = None
    status: str  # "not_started" | "active" | "closed"
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    question_count: int = 0


class OfflinePollJoinResponse(BaseModel):
    """Response when joining / resuming an offline poll"""
    session_token: str
    participant_id: int
    quiz_title: str
    questions: List[QuestionResponse] = []
    saved_answers: List[dict] = []  # [{question_id, selected_option_index, text_answer}]
    ends_at: Optional[datetime] = None


class OfflineAnswerRequest(BaseModel):
    """Save one answer for an offline poll (upsert)"""
    session_token: str
    question_id: int
    selected_option_index: Optional[int] = Field(None, ge=0)
    text_answer: Optional[str] = Field(None, min_length=1, max_length=2000)


class OfflineCompleteRequest(BaseModel):
    """Mark an offline poll as completed"""
    session_token: str


class OfflineResultsQuestionResponse(BaseModel):
    """Per-question results for an offline poll"""
    question_id: int
    question_text: str
    question_type: str
    options: Optional[List[str]] = None
    answer_distribution: Optional[List[int]] = None  # MCQ: count per option
    word_frequencies: Optional[dict] = None  # word_cloud: {word: count}
    total_answers: int


class OfflineResultsResponse(BaseModel):
    """Aggregated results for an offline poll (auth required)"""
    quiz_id: int
    quiz_title: str
    slug: Optional[str] = None
    offline_start_at: Optional[datetime] = None
    offline_end_at: Optional[datetime] = None
    is_open: bool
    total_participants: int
    completed_participants: int
    question_results: List[OfflineResultsQuestionResponse]


class OfflinePollPublishResponse(BaseModel):
    """Response after publishing an offline poll"""
    poll_url: str
    poll_slug: str
    quiz_id: int


# Exam Schemas
class ExamPublishResponse(BaseModel):
    """Response after publishing an exam"""
    exam_url: str
    exam_slug: str
    quiz_id: int


class ExamInfoResponse(BaseModel):
    """Public info about an exam (no auth required)"""
    quiz_id: Optional[int] = None
    slug: str
    title: str
    description: Optional[str] = None
    status: str  # "upcoming" | "open" | "closed"
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    question_count: int = 0
    time_limit_seconds: Optional[int] = None
    has_per_question_timers: bool = False
    require_email: bool = False
    # Scoring summary
    points_per_correct: int = 1
    negative_points_per_wrong: int = 0
    scoring_varies: bool = False


class ExamOtpRequest(BaseModel):
    """Request an OTP be sent to participant's email"""
    display_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr


class ExamStartRequest(BaseModel):
    """Start an exam (participant). email+otp required only when exam.require_email is True."""
    display_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    otp: Optional[str] = Field(None, min_length=6, max_length=6)


class ExamQuestionResponse(BaseModel):
    """Question as seen during exam (no correct answer revealed)"""
    id: int
    text: str
    options: Optional[List[str]] = None
    order: int
    question_image_url: Optional[str] = None
    option_images: Optional[dict] = None
    points: int = 1
    max_time_seconds: Optional[int] = None

    class Config:
        from_attributes = True


class ExamStartResponse(BaseModel):
    """Response when starting an exam"""
    session_token: str
    participant_id: int
    quiz_title: str
    questions: List[ExamQuestionResponse] = []
    started_at: datetime
    time_limit_seconds: Optional[int] = None
    ends_at: Optional[datetime] = None


class ExamAnswerRequest(BaseModel):
    """Save one answer during exam"""
    session_token: str
    question_id: int
    selected_option_index: Optional[int] = Field(None, ge=0)


class ExamSubmitRequest(BaseModel):
    """Submit the exam"""
    session_token: str


class AnalyzeResultsRequest(BaseModel):
    """Optional custom prompt for AI analysis"""
    custom_prompt: Optional[str] = None


class ExamQuestionResult(BaseModel):
    """Per-question result shown to participant after submission"""
    question_id: int
    question_text: str
    options: Optional[List[str]] = None
    correct_answer_index: Optional[int] = None
    participant_answer: Optional[int] = None
    is_correct: Optional[bool] = None
    points_earned: int = 0
    points_possible: int = 1
    negative_points_applied: int = 0
    answer_explanation: Optional[str] = None


class ExamSubmitResponse(BaseModel):
    """Score shown immediately after submit"""
    total_score: int
    max_score: int
    percentage: float
    correct_count: int
    wrong_count: int
    unanswered_count: int
    question_results: List[ExamQuestionResult]


class ExamLeaderboardEntry(BaseModel):
    """Single entry in host's exam leaderboard"""
    participant_id: Optional[int] = None
    rank: Optional[int] = None
    display_name: str
    email: Optional[str] = None
    score: int
    max_score: int
    percentage: float
    correct_count: int
    time_taken_seconds: Optional[float] = None
    completed_at: Optional[datetime] = None
    is_abandoned: bool = False
    is_completed: bool = False


class ParticipantQuestionResult(BaseModel):
    """Per-question result for a single participant (host view)"""
    question_id: int
    order: int
    question_text: str
    options: Optional[List[str]] = None
    correct_answer_index: Optional[int] = None
    participant_answer: Optional[int] = None
    is_correct: Optional[bool] = None
    points_earned: int = 0
    points_possible: int = 1


class ParticipantDetailResponse(BaseModel):
    """Full per-participant breakdown for host"""
    participant_id: int
    display_name: str
    email: Optional[str] = None
    score: int
    max_score: int
    percentage: float
    correct_count: int
    wrong_count: int
    unanswered_count: int
    time_taken_seconds: Optional[float] = None
    completed_at: Optional[datetime] = None
    questions: List[ParticipantQuestionResult]


class ExamQuestionAnalytics(BaseModel):
    """Per-question analytics for host"""
    question_id: int
    question_text: str
    options: Optional[List[str]] = None
    correct_answer_index: Optional[int] = None
    answer_distribution: List[int] = []
    correct_count: int = 0
    total_answers: int = 0
    percent_correct: float = 0.0


class ExamResultsResponse(BaseModel):
    """Full results for host dashboard"""
    quiz_id: int
    quiz_title: str
    slug: Optional[str] = None
    exam_start_at: Optional[datetime] = None
    exam_end_at: Optional[datetime] = None
    is_open: bool
    total_started: int
    total_completed: int
    total_abandoned: int
    average_score: float
    max_score: int
    leaderboard: List[ExamLeaderboardEntry]
    question_analytics: List[ExamQuestionAnalytics]
    participant_emails_sent: bool = False
