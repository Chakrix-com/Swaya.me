"""
Quiz feature domain models
"""
from sqlalchemy import Column, Integer, BigInteger, Float, String, Boolean, Enum as SQLEnum, ForeignKey, Text, JSON, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import DATETIME as MYSQL_DATETIME, LONGTEXT as MYSQL_LONGTEXT
from sqlalchemy.orm import relationship
import enum

from persistence.database import Base
from persistence.models.base import TimestampMixin, TenantMixin


class QuizStatus(str, enum.Enum):
    """Quiz definition status"""
    DRAFT = "draft"
    READY = "ready"
    ARCHIVED = "archived"


class QuizType(str, enum.Enum):
    """Quiz experience type"""
    QUIZ = "quiz"
    POLL = "poll"
    OFFLINE_POLL = "offline_poll"
    EXAM = "exam"
    CODING_CHALLENGE = "coding_challenge"


class QuizSessionStatus(str, enum.Enum):
    """Quiz session status"""
    CREATED = "created"
    ACTIVE = "active"
    ENDED = "ended"


class QuestionStatus(str, enum.Enum):
    """Question status during session"""
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"


class QuestionType(str, enum.Enum):
    """Question type"""
    MCQ = "mcq"
    WORD_CLOUD = "word_cloud"
    SINGLE_LINE = "single_line"
    SCALE = "scale"
    PARAGRAPH = "paragraph"
    ONE_WORD = "one_word"
    CODE = "code"
    MCQ_MULTI = "mcq_multi"
    CODING_CHALLENGE = "coding_challenge"


class TemplateScope(str, enum.Enum):
    """Template visibility scope"""
    TENANT = "tenant"
    GLOBAL = "global"


class Quiz(Base, TimestampMixin, TenantMixin):
    """
    Quiz definition - the authored content
    """
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    folder_id = Column(Integer, ForeignKey('quiz_folders.id', ondelete='SET NULL'), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    quiz_type = Column(
        SQLEnum(QuizType, values_callable=lambda obj: [e.value for e in obj]),
        default=QuizType.QUIZ,
        nullable=False,
        server_default=QuizType.QUIZ.value,
    )
    status = Column(SQLEnum(QuizStatus), default=QuizStatus.DRAFT, nullable=False)
    is_template = Column(Boolean, default=False, nullable=False, server_default="0")
    template_scope = Column(
        SQLEnum(TemplateScope, values_callable=lambda obj: [e.value for e in obj]),
        default=TemplateScope.TENANT,
        nullable=False,
        server_default=TemplateScope.TENANT.value,
    )

    # Offline poll fields
    poll_slug = Column(String(64), nullable=True, unique=True, index=True)
    offline_start_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)
    offline_end_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)
    offline_results_email = Column(String(255), nullable=True)
    offline_session_id = Column(Integer, ForeignKey('quiz_sessions.id'), nullable=True)

    # Exam fields
    exam_slug = Column(String(64), nullable=True, unique=True, index=True)
    exam_start_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)
    exam_end_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)
    exam_time_limit_seconds = Column(Integer, nullable=True)
    exam_session_id = Column(Integer, ForeignKey('quiz_sessions.id'), nullable=True)
    exam_results_email = Column(String(255), nullable=True)
    exam_require_email = Column(Boolean, default=False, nullable=False, server_default="0")
    exam_allowed_domains = Column(Text, nullable=True)
    exam_participant_emails_sent = Column(Boolean, default=False, nullable=False, server_default="0")
    linked_exam_session_ids = Column(JSON, nullable=True)

    # Proctoring
    proctoring_policy = Column(JSON, nullable=True)

    # Archive
    archived_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)

    # Participant skin (visual theme for audience + projector view)
    skin = Column(String(32), nullable=True)

    # Emoji reaction style for participant feedback (null = disabled)
    reaction_style = Column(String(32), nullable=True)

    # Quiz behaviour
    shuffle_questions = Column(Boolean, default=False, nullable=False, server_default="0")
    shuffle_options = Column(Boolean, default=False, nullable=False, server_default="0")
    default_question_time_seconds = Column(Integer, nullable=True)

    # Template gallery metadata
    template_category = Column(String(64), nullable=True)
    template_use_count = Column(Integer, default=0, nullable=False, server_default="0")

    # Relationships
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")
    sessions = relationship("QuizSession", back_populates="quiz", foreign_keys="QuizSession.quiz_id")
    folder = relationship("QuizFolder", back_populates="quizzes")


class QuizFolder(Base, TimestampMixin, TenantMixin):
    """Nested folder for organizing quizzes and polls."""
    __tablename__ = "quiz_folders"
    __table_args__ = (
        UniqueConstraint("tenant_id", "parent_id", "name", name="uq_quiz_folders_tenant_parent_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("quiz_folders.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    parent = relationship("QuizFolder", remote_side=[id], back_populates="children")
    children = relationship("QuizFolder", back_populates="parent", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="folder")
    shares = relationship("FolderShare", back_populates="folder", cascade="all, delete-orphan")


class FolderShare(Base):
    """Grants a tenant user read (or edit) access to a folder they don't own."""
    __tablename__ = "folder_shares"
    __table_args__ = (
        UniqueConstraint("folder_id", "shared_with_user_id", name="uq_folder_shares"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    folder_id = Column(Integer, ForeignKey("quiz_folders.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_with_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    can_edit = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    folder = relationship("QuizFolder", back_populates="shares")


class CodingResultVisibility(str, enum.Enum):
    """How much of a graded coding-challenge result the candidate sees. Always
    gated on submission status == GRADED regardless of this value — see
    /coding-challenge/{token}/status."""
    HIDDEN = "hidden"
    STATUS_ONLY = "status_only"
    FULL = "full"


class Question(Base, TimestampMixin):
    """
    Question definition - part of a quiz
    """
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey('quizzes.id'), nullable=False)
    question_type = Column(SQLEnum(QuestionType, values_callable=lambda obj: [e.value for e in obj]), default=QuestionType.MCQ, nullable=False)
    text = Column(Text, nullable=False)
    order = Column(Integer, nullable=False)
    options = Column(JSON, nullable=True)  # List of 4 options for MCQ, null for word_cloud
    correct_answer_index = Column(Integer, nullable=True)  # 0-3 for MCQ, null for word_cloud
    correct_answer_indices = Column(JSON, nullable=True)  # list[int], mcq_multi only
    reveal_answer_count = Column(Boolean, nullable=False, default=False, server_default="0")  # mcq_multi only
    question_image_url = Column(String(500), nullable=True)  # Optional image for question text
    question_video_url = Column(String(500), nullable=True)  # Optional YouTube/Vimeo embed URL
    option_images = Column(JSON, nullable=True)  # Optional images for MCQ options: {"A": "path", "B": "path", ...}
    points = Column(Float, nullable=False, default=1, server_default="1")
    max_time_seconds = Column(Integer, nullable=True)
    negative_points = Column(Float, nullable=False, default=0, server_default="0")
    is_required = Column(Boolean, nullable=False, default=False, server_default="0")
    answer_explanation = Column(Text, nullable=True)
    grading_rubric = Column(Text, nullable=True)

    # CODING_CHALLENGE fields
    git_repo_url = Column(String(500), nullable=True)
    test_command = Column(String(255), nullable=True, default="pytest -q", server_default="pytest -q")
    hidden_test_content = Column(Text, nullable=True)
    hidden_test_filename = Column(String(255), nullable=True)
    time_budget_seconds = Column(Integer, nullable=True)
    # Host-overridden grading criteria weights (percentages, must sum to 100).
    # Null = use the platform default weights (grading_service_async._WEIGHTS).
    grading_weights = Column(JSON, nullable=True)
    result_visibility = Column(
        SQLEnum(CodingResultVisibility, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False, default=CodingResultVisibility.HIDDEN, server_default="hidden",
    )

    # Relationships
    quiz = relationship("Quiz", back_populates="questions")
    answers = relationship("Answer", back_populates="question")


class CodeWorkspaceStatus(str, enum.Enum):
    """Coding-challenge Coder workspace lifecycle status"""
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUBMITTED = "submitted"
    ABANDONED = "abandoned"
    DESTROYED = "destroyed"
    PROVISION_FAILED = "provision_failed"


class CodeWorkspace(Base, TimestampMixin, TenantMixin):
    """
    A candidate's per-workspace Coder sandbox for a CODING_CHALLENGE question.
    """
    __tablename__ = "code_workspaces"
    __table_args__ = (
        # One row per attempt, not per candidate — attempt_number lets a host grant a
        # re-invite after a terminal attempt without colliding with the prior one.
        UniqueConstraint('quiz_id', 'question_id', 'candidate_email', 'attempt_number',
                          name='uq_code_workspace_quiz_question_email_attempt'),
    )

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey('quizzes.id'), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False, index=True)
    candidate_email = Column(String(255), nullable=False, index=True)
    attempt_number = Column(Integer, nullable=False, default=1, server_default="1")
    ide_type = Column(String(20), nullable=False)  # code_server | intellij
    coder_workspace_name = Column(String(255), nullable=False, unique=True)
    coder_token_name = Column(String(255), nullable=True)
    status = Column(
        SQLEnum(CodeWorkspaceStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=CodeWorkspaceStatus.PROVISIONING,
        nullable=False,
        server_default=CodeWorkspaceStatus.PROVISIONING.value,
    )
    workspace_url = Column(String(1000), nullable=True)
    submitted_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)
    destroyed_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)

    # Relationships
    quiz = relationship("Quiz")
    question = relationship("Question")
    submission = relationship("CodeSubmission", back_populates="workspace", uselist=False)


class CodingChallengeInvite(Base, TimestampMixin, TenantMixin):
    """
    Tracks that a candidate was invited to a CODING_CHALLENGE question. The
    invite link itself is a stateless signed JWT — this table is the only
    record of "who was invited" that exists before (or absent) the candidate
    ever starting, since CodeWorkspace isn't created until they do.
    created_at = first invited, updated_at = most recently re-invited (used
    to derive Pending/Expired status against the JWT's fixed validity window,
    rather than storing a status that could drift out of sync).
    """
    __tablename__ = "coding_challenge_invites"
    __table_args__ = (
        UniqueConstraint('quiz_id', 'question_id', 'candidate_email', name='uq_cc_invite_quiz_question_email'),
    )

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, index=True)
    candidate_email = Column(String(255), nullable=False, index=True)
    invited_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    email_sent = Column(Boolean, nullable=False, default=True, server_default="1")
    # Which attempt the most recent invite email targets — lets the review screen
    # show "re-invited, awaiting attempt 2" even though no CodeWorkspace row exists
    # yet for that attempt (one isn't created until the candidate actually starts).
    latest_invited_attempt_number = Column(Integer, nullable=False, default=1, server_default="1")

    # Relationships
    quiz = relationship("Quiz")
    question = relationship("Question")


class CodeSubmissionStatus(str, enum.Enum):
    """Coding-challenge grading pipeline status"""
    QUEUED = "queued"
    GRADING = "grading"
    GRADED = "graded"
    FAILED = "failed"
    PARTIAL_FAILED = "partial_failed"


class CodeSubmission(Base, TimestampMixin):
    """
    A candidate's submitted coding-challenge solution and its (possibly async, possibly
    partial) grading outcome. Inserted at /submit time, not at /start.
    """
    __tablename__ = "code_submissions"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey('code_workspaces.id'), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False, index=True)
    test_output = Column(MYSQL_LONGTEXT, nullable=True)
    passed_count = Column(Integer, nullable=True)
    total_count = Column(Integer, nullable=True)
    ai_transcript_raw = Column(MYSQL_LONGTEXT, nullable=True)
    code_timeline = Column(MYSQL_LONGTEXT, nullable=True)
    ai_token_usage = Column(JSON, nullable=True)
    score_breakdown = Column(JSON, nullable=True)
    ai_score = Column(Integer, nullable=True)
    ai_verdict = Column(String(50), nullable=True)
    ai_rationale = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    status = Column(
        SQLEnum(CodeSubmissionStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=CodeSubmissionStatus.QUEUED,
        nullable=False,
        server_default=CodeSubmissionStatus.QUEUED.value,
    )
    submitted_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)
    graded_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)

    # Relationships
    workspace = relationship("CodeWorkspace", back_populates="submission")
    question = relationship("Question")


class QuizSession(Base, TimestampMixin, TenantMixin):
    """
    Quiz session - a live instance of a quiz
    """
    __tablename__ = "quiz_sessions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey('quizzes.id'), nullable=False)
    status = Column(SQLEnum(QuizSessionStatus), default=QuizSessionStatus.CREATED, nullable=False)
    current_question_index = Column(Integer, default=-1, nullable=False)
    current_question_status = Column(SQLEnum(QuestionStatus), default=QuestionStatus.PENDING, nullable=True)
    leaderboard_visible = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    quiz = relationship("Quiz", back_populates="sessions", foreign_keys=[quiz_id])
    participants = relationship("Participant", back_populates="session")
    answers = relationship("Answer", back_populates="session")
    question_timings = relationship("SessionQuestionTiming", back_populates="session", cascade="all, delete-orphan")


class Participant(Base, TimestampMixin):
    """
    Participant - anonymous audience member in a session
    """
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('quiz_sessions.id'), nullable=False)
    display_name = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    completed_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)
    started_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)
    last_activity_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)
    is_abandoned = Column(Boolean, default=False, nullable=False, server_default="0")
    result_email_sent = Column(Boolean, default=False, nullable=False, server_default="0")
    certificate_token = Column(String(36), unique=True, nullable=True, index=True)

    # Relationships
    session = relationship("QuizSession", back_populates="participants")
    answers = relationship("Answer", back_populates="participant")


class Answer(Base, TimestampMixin):
    """
    Answer - participant's response to a question
    """
    __tablename__ = "answers"
    __table_args__ = (
        UniqueConstraint('participant_id', 'question_id', name='uq_answer_participant_question'),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('quiz_sessions.id'), nullable=False)
    participant_id = Column(Integer, ForeignKey('participants.id'), nullable=False)
    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False)
    selected_option_index = Column(Integer, nullable=True)  # 0-3 for MCQ, null for word_cloud
    selected_option_indices = Column(JSON, nullable=True)  # list[int], mcq_multi only
    text_answer = Column(Text, nullable=True)  # For text-based questions
    is_correct = Column(Boolean, nullable=True)  # For MCQ only, null for word_cloud
    ai_feedback = Column(Text, nullable=True)  # For CODE questions: verdict + simulated output
    
    # Relationships
    session = relationship("QuizSession", back_populates="answers")
    participant = relationship("Participant", back_populates="answers")
    question = relationship("Question", back_populates="answers")


class SessionQuestionTiming(Base):
    """
    Tracks when each question was displayed and closed during a session.
    Multiple rows per question are allowed (host may go back and re-show a question).
    """
    __tablename__ = "session_question_timings"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('quiz_sessions.id'), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False)
    question_index = Column(Integer, nullable=False)
    opened_at = Column(MYSQL_DATETIME(fsp=6), nullable=False)
    closed_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)

    session = relationship("QuizSession", back_populates="question_timings")
    question = relationship("Question")


class QuizFeedback(Base, TimestampMixin, TenantMixin):
    """
    Feedback submitted by participants or authenticated users for a quiz/session
    """
    __tablename__ = "quiz_feedback"
    __table_args__ = (
        UniqueConstraint('participant_id', 'session_id', name='uq_feedback_participant_session'),
    )

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey('quizzes.id'), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey('quiz_sessions.id'), nullable=True, index=True)
    participant_id = Column(Integer, ForeignKey('participants.id'), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    source_type = Column(String(20), nullable=False)  # participant | user
    display_name = Column(String(100), nullable=True)
    rating = Column(Integer, nullable=True)
    feedback_text = Column(Text, nullable=True)
    reaction = Column(String(32), nullable=True)


class PlatformEvent(Base):
    """Lightweight analytics beacon — fires-and-forgets, never blocks a request."""
    __tablename__ = "platform_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_type = Column(String(64), nullable=False, index=True)
    tenant_id = Column(Integer, nullable=True, index=True)
    user_id = Column(Integer, nullable=True)
    session_id = Column(Integer, nullable=True)
    quiz_id = Column(Integer, nullable=True)
    properties = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
