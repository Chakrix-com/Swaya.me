"""add proctoring tables

Revision ID: h1i2j3k4l5m6
Revises: g7h8i9j0k1l2
Create Date: 2026-04-19 09:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME as MYSQL_DATETIME

revision: str = 'h1i2j3k4l5m6'
down_revision: Union[str, None] = 'g7h8i9j0k1l2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # 1. platform_proctoring_rules
    if 'platform_proctoring_rules' not in existing_tables:
        op.create_table(
            'platform_proctoring_rules',
            sa.Column('id', sa.BigInteger(), autoincrement=True, primary_key=True),
            sa.Column('rule_id', sa.String(64), nullable=False, unique=True),
            sa.Column('display_name', sa.String(128), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('applies_to', sa.JSON(), nullable=False),
            sa.Column('tier_minimum', sa.Enum('free', 'basic', 'pro', 'enterprise', name='tier_minimum_enum'), nullable=False),
            sa.Column('config_schema', sa.JSON(), nullable=False),
            sa.Column('default_config', sa.JSON(), nullable=False),
            sa.Column('severity', sa.Enum('warn', 'lock', name='severity_enum'), nullable=False, server_default='warn'),
            sa.Column('is_silent', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('created_at', MYSQL_DATETIME(fsp=6), nullable=False,
                      server_default=sa.text('CURRENT_TIMESTAMP(6)')),
        )

    # 2. tenant_proctoring_policies
    if 'tenant_proctoring_policies' not in existing_tables:
        op.create_table(
            'tenant_proctoring_policies',
            sa.Column('id', sa.BigInteger(), autoincrement=True, primary_key=True),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('rule_id', sa.String(64), nullable=False),
            sa.Column('enabled_for', sa.JSON(), nullable=False),
            sa.Column('config_override', sa.JSON(), nullable=True),
            sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('updated_at', MYSQL_DATETIME(fsp=6), nullable=True),
            sa.Column('updated_by', sa.Integer(), nullable=True),
            sa.UniqueConstraint('tenant_id', 'rule_id', name='uq_tenant_rule'),
        )

    # 3. proctoring_sessions
    if 'proctoring_sessions' not in existing_tables:
        op.create_table(
            'proctoring_sessions',
            sa.Column('id', sa.BigInteger(), autoincrement=True, primary_key=True),
            sa.Column('participant_id', sa.Integer(), nullable=False),
            sa.Column('quiz_id', sa.Integer(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('active_rule_set', sa.JSON(), nullable=False),
            sa.Column('violation_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('integrity_score', sa.Integer(), nullable=False, server_default='100'),
            sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('locked_at', MYSQL_DATETIME(fsp=6), nullable=True),
            sa.Column('lock_reason', sa.String(100), nullable=True),
            sa.Column('browser_fingerprint', sa.String(64), nullable=True),
            sa.Column('ip_address', sa.String(45), nullable=True),
            sa.Column('user_agent', sa.Text(), nullable=True),
            sa.Column('webcam_required', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('webcam_granted', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('session_started_at', MYSQL_DATETIME(fsp=6), nullable=True),
            sa.UniqueConstraint('participant_id', 'quiz_id', name='uq_participant_quiz'),
        )
        op.create_index('idx_proctor_sess_participant', 'proctoring_sessions', ['participant_id'])
        op.create_index('idx_proctor_sess_quiz', 'proctoring_sessions', ['quiz_id'])

    # 4. proctoring_events
    if 'proctoring_events' not in existing_tables:
        op.create_table(
            'proctoring_events',
            sa.Column('id', sa.BigInteger(), autoincrement=True, primary_key=True),
            sa.Column('quiz_id', sa.Integer(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('participant_id', sa.Integer(), nullable=False),
            sa.Column('session_token', sa.String(255), nullable=False),
            sa.Column('rule_id', sa.String(64), nullable=True),
            sa.Column('event_type', sa.String(64), nullable=False),
            sa.Column('occurred_at', MYSQL_DATETIME(fsp=6), nullable=False,
                      server_default=sa.text('CURRENT_TIMESTAMP(6)')),
            sa.Column('metadata', sa.JSON(), nullable=True),
        )
        op.create_index('idx_proctor_evt_token', 'proctoring_events', ['session_token'])
        op.create_index('idx_proctor_evt_quiz_participant', 'proctoring_events', ['quiz_id', 'participant_id'])

    # 5. Add proctoring_policy column to quizzes
    quiz_columns = {col['name'] for col in inspector.get_columns('quizzes')}
    if 'proctoring_policy' not in quiz_columns:
        op.add_column('quizzes', sa.Column('proctoring_policy', sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    quiz_columns = {col['name'] for col in inspector.get_columns('quizzes')}
    if 'proctoring_policy' in quiz_columns:
        op.drop_column('quizzes', 'proctoring_policy')

    if 'proctoring_events' in existing_tables:
        op.drop_table('proctoring_events')
    if 'proctoring_sessions' in existing_tables:
        op.drop_table('proctoring_sessions')
    if 'tenant_proctoring_policies' in existing_tables:
        op.drop_table('tenant_proctoring_policies')
    if 'platform_proctoring_rules' in existing_tables:
        op.drop_table('platform_proctoring_rules')
