"""add_participant_emails_sent_to_quizzes

Revision ID: f3g4h5i6j7k8
Revises: e2f3a4b5c6d7
Create Date: 2026-05-16 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f3g4h5i6j7k8'
down_revision: Union[str, None] = 'e2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('quizzes', sa.Column(
        'exam_participant_emails_sent',
        sa.Boolean(),
        nullable=False,
        server_default='0',
    ))


def downgrade() -> None:
    op.drop_column('quizzes', 'exam_participant_emails_sent')
