"""add template_category and template_use_count to quizzes

Revision ID: 20260613_1000
Revises: 20260612_1000
Create Date: 2026-06-13
"""
from alembic import op
import sqlalchemy as sa

revision = '20260613_1000'
down_revision = '20260612_1000'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('quizzes', sa.Column('template_category', sa.String(64), nullable=True))
    op.add_column('quizzes', sa.Column('template_use_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('quizzes', 'template_use_count')
    op.drop_column('quizzes', 'template_category')
