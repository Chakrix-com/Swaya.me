"""add shuffle_questions, shuffle_options, default_question_time_seconds to quizzes

Revision ID: 20260705_1200
Revises: 20260703_1200
Create Date: 2026-07-05 12:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '20260705_1200'
down_revision = '20260703_1200'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('quizzes', sa.Column('shuffle_questions', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('quizzes', sa.Column('shuffle_options', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('quizzes', sa.Column('default_question_time_seconds', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('quizzes', 'default_question_time_seconds')
    op.drop_column('quizzes', 'shuffle_options')
    op.drop_column('quizzes', 'shuffle_questions')
