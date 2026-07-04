"""add code question type with grading_rubric and ai_feedback columns

Revision ID: 20260703_1200
Revises: 20260625_1200
Create Date: 2026-07-03 12:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '20260703_1200'
down_revision = '20260625_1200'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE questions "
        "MODIFY COLUMN question_type "
        "ENUM('mcq','word_cloud','single_line','scale','paragraph','one_word','code') "
        "NOT NULL"
    )
    op.add_column('questions', sa.Column('grading_rubric', sa.Text(), nullable=True))
    op.add_column('answers', sa.Column('ai_feedback', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('answers', 'ai_feedback')
    op.drop_column('questions', 'grading_rubric')
    op.execute(
        "ALTER TABLE questions "
        "MODIFY COLUMN question_type "
        "ENUM('mcq','word_cloud','single_line','scale','paragraph','one_word') "
        "NOT NULL"
    )
