"""Add leaderboard_visible to quiz_sessions

Revision ID: t4u5v6w7x8y9
Revises: s3t4u5v6w7x8
Create Date: 2026-03-02 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 't4u5v6w7x8y9'
down_revision = 's3t4u5v6w7x8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'quiz_sessions',
        sa.Column('leaderboard_visible', sa.Boolean(), nullable=False, server_default='1')
    )


def downgrade():
    op.drop_column('quiz_sessions', 'leaderboard_visible')
