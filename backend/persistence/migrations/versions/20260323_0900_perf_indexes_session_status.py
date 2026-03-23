"""Add performance indexes on quiz_sessions.status and updated_at

Revision ID: 20260323_0900
Revises: 20260322_1000
Create Date: 2026-03-23

These indexes eliminate table scans in _close_stale_sessions (called on every
participant join) which filters quiz_sessions by (tenant_id, status, updated_at).
Without indexes on status and updated_at the query does a partial scan even when
tenant_id is indexed — causing O(n_sessions) work per join under load.
"""
from alembic import op

# revision identifiers
revision = '20260323_0900'
down_revision = '20260322_1200'  # revision ID: 20260322_1200
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        'ix_quiz_sessions_status',
        'quiz_sessions',
        ['status'],
        unique=False,
    )
    op.create_index(
        'ix_quiz_sessions_updated_at',
        'quiz_sessions',
        ['updated_at'],
        unique=False,
    )
    # Composite index for the exact query in _close_stale_sessions:
    # WHERE tenant_id = ? AND status IN (...) AND updated_at < ?
    op.create_index(
        'ix_quiz_sessions_tenant_status_updated',
        'quiz_sessions',
        ['tenant_id', 'status', 'updated_at'],
        unique=False,
    )


def downgrade():
    op.drop_index('ix_quiz_sessions_tenant_status_updated', table_name='quiz_sessions')
    op.drop_index('ix_quiz_sessions_updated_at', table_name='quiz_sessions')
    op.drop_index('ix_quiz_sessions_status', table_name='quiz_sessions')
