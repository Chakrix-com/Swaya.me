"""add skin column to quizzes

Revision ID: 20260613_0300
Revises: 20260612_1000_add_archived_at_to_quizzes
Create Date: 2026-06-13 03:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = '20260613_0300'
down_revision = '20260613_1000'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('quizzes', sa.Column('skin', sa.String(32), nullable=True, server_default=None))


def downgrade():
    op.drop_column('quizzes', 'skin')
