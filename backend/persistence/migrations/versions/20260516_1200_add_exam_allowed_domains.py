"""add_exam_allowed_domains

Revision ID: g4h5i6j7k8l9
Revises: f3g4h5i6j7k8
Create Date: 2026-05-16 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'g4h5i6j7k8l9'
down_revision: Union[str, None] = 'f3g4h5i6j7k8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('quizzes', sa.Column('exam_allowed_domains', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('quizzes', 'exam_allowed_domains')
