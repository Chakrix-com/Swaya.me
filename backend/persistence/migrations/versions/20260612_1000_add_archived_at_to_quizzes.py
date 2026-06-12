"""add archived_at to quizzes

Revision ID: 20260612_1000
Revises: 20260529_1200
Create Date: 2026-06-12
"""
from alembic import op
import sqlalchemy as sa

revision = '20260612_1000'
down_revision = '20260529_1200'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'quizzes',
        sa.Column('archived_at', sa.DateTime(timezone=False), nullable=True)
    )


def downgrade():
    op.drop_column('quizzes', 'archived_at')
