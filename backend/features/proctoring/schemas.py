"""
Pydantic schemas for proctoring module
"""
from pydantic import BaseModel
from typing import Optional


class ProctoringContext(BaseModel):
    quiz_id: int
    tenant_id: int
    quiz_type: str
    tier: str
    host_enabled: bool


class ResolvedRule(BaseModel):
    rule_id: str
    display_name: str
    severity: str
    is_silent: bool
    config: dict


class ResolvedRuleSet(BaseModel):
    enabled: bool
    rules: list[ResolvedRule]
    escalation: dict
    webcam_required: bool


class SessionInitRequest(BaseModel):
    quiz_id: int
    browser_fingerprint: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    webcam_granted: bool = False


class SessionInitResponse(BaseModel):
    session_token: str
    rule_set: ResolvedRuleSet


class ViolationEventRequest(BaseModel):
    session_token: str
    rule_id: str
    event_type: str
    metadata: dict = {}


class ViolationEventResponse(BaseModel):
    logged: bool
    is_locked: bool
    violations_remaining: Optional[int]
    silent: bool


class BiometricSample(BaseModel):
    session_token: str
    mouse_path: list[dict]
    keystroke_intervals: list[int]
    backspace_count: int
    scroll_events: list[dict]
    time_to_first_interaction_ms: int


class AnswerTimingRequest(BaseModel):
    session_token: str
    question_id: int
    question_type: str
    question_word_count: int
    elapsed_ms: int


class AnswerTimingResponse(BaseModel):
    accepted: bool
    reason: Optional[str] = None
    wait_ms: Optional[int] = None


class HoneypotRequest(BaseModel):
    session_token: Optional[str] = None
    trap: Optional[str] = None
    t: Optional[str] = None


class ViolationReportEntry(BaseModel):
    participant_id: int
    display_name: Optional[str]
    integrity_score: int
    violation_count: int
    is_locked: bool
    events: list[dict]


class TenantPolicyUpdate(BaseModel):
    rule_id: str
    is_enabled: bool
    enabled_for: dict = {}
    config_override: Optional[dict] = None


class PlatformRuleUpdate(BaseModel):
    is_active: Optional[bool] = None
    tier_minimum: Optional[str] = None
    default_config: Optional[dict] = None
    severity: Optional[str] = None
