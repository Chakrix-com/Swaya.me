"""
Proctoring domain models
"""
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, Enum as SQLEnum, Text, JSON, ForeignKey
from sqlalchemy.dialects.mysql import DATETIME as MYSQL_DATETIME
import sqlalchemy as sa

from persistence.database import Base


class PlatformProctoringRule(Base):
    __tablename__ = "platform_proctoring_rules"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    rule_id = Column(String(64), nullable=False, unique=True, index=True)
    display_name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    applies_to = Column(JSON, nullable=False)
    tier_minimum = Column(SQLEnum('free', 'basic', 'pro', 'enterprise', name='tier_minimum_enum'), nullable=False)
    config_schema = Column(JSON, nullable=False)
    default_config = Column(JSON, nullable=False)
    severity = Column(SQLEnum('warn', 'lock', name='severity_enum'), nullable=False, server_default='warn')
    is_silent = Column(Boolean, nullable=False, default=False, server_default='0')
    is_active = Column(Boolean, nullable=False, default=True, server_default='1')
    created_at = Column(MYSQL_DATETIME(fsp=6), nullable=False,
                        server_default=sa.text('CURRENT_TIMESTAMP(6)'))


class TenantProctoringPolicy(Base):
    __tablename__ = "tenant_proctoring_policies"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    rule_id = Column(String(64), nullable=False)
    enabled_for = Column(JSON, nullable=False)
    config_override = Column(JSON, nullable=True)
    is_enabled = Column(Boolean, nullable=False, default=True, server_default='1')
    updated_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)
    updated_by = Column(Integer, nullable=True)


class ProctoringSession(Base):
    __tablename__ = "proctoring_sessions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    participant_id = Column(Integer, ForeignKey('participants.id', ondelete='CASCADE'), nullable=False, index=True)
    quiz_id = Column(Integer, ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    active_rule_set = Column(JSON, nullable=False)
    violation_count = Column(Integer, nullable=False, default=0, server_default='0')
    integrity_score = Column(Integer, nullable=False, default=100, server_default='100')
    is_locked = Column(Boolean, nullable=False, default=False, server_default='0')
    locked_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)
    lock_reason = Column(String(100), nullable=True)
    browser_fingerprint = Column(String(512), nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    webcam_required = Column(Boolean, nullable=False, default=False, server_default='0')
    webcam_granted = Column(Boolean, nullable=False, default=False, server_default='0')
    session_started_at = Column(MYSQL_DATETIME(fsp=6), nullable=True)


class ProctoringEvent(Base):
    __tablename__ = "proctoring_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    quiz_id = Column(Integer, ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False)
    tenant_id = Column(Integer, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    participant_id = Column(Integer, ForeignKey('participants.id', ondelete='CASCADE'), nullable=False)
    session_token = Column(String(255), nullable=False, index=True)
    rule_id = Column(String(64), nullable=True)
    event_type = Column(String(64), nullable=False)
    occurred_at = Column(MYSQL_DATETIME(fsp=6), nullable=False,
                         server_default=sa.text('CURRENT_TIMESTAMP(6)'))
    event_metadata = Column('metadata', JSON, nullable=True)
