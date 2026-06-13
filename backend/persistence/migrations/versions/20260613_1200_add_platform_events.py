"""add_platform_events

Revision ID: 20260613_1200
Revises: 20260613_1000
Create Date: 2026-06-13 12:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '20260613_1200'
down_revision = ('20260613_0300', '20260613_1000')
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'platform_events',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('event_type', sa.String(64), nullable=False, index=True),
        sa.Column('tenant_id', sa.Integer(), nullable=True, index=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('quiz_id', sa.Integer(), nullable=True),
        sa.Column('properties', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), index=True),
    )


def downgrade():
    op.drop_table('platform_events')
