"""add reaction_style to quizzes, reaction to quiz_feedback

Revision ID: 20260618_1800
Revises: 20260614_1200
Create Date: 2026-06-18 18:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '20260618_1800'
down_revision = '20260614_1200'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('quizzes', sa.Column('reaction_style', sa.String(32), nullable=True))
    op.add_column('quiz_feedback', sa.Column('reaction', sa.String(32), nullable=True))
    op.alter_column('quiz_feedback', 'feedback_text', existing_type=sa.Text(), nullable=True)


def downgrade():
    op.alter_column('quiz_feedback', 'feedback_text', existing_type=sa.Text(), nullable=False)
    op.drop_column('quiz_feedback', 'reaction')
    op.drop_column('quizzes', 'reaction_style')
