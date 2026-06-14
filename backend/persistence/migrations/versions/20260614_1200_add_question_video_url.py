"""add question_video_url to questions

Revision ID: 20260614_1200
Revises: 20260614_0900
Create Date: 2026-06-14 12:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '20260614_1200'
down_revision = '20260614_0900'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('questions', sa.Column('question_video_url', sa.String(500), nullable=True))


def downgrade():
    op.drop_column('questions', 'question_video_url')
