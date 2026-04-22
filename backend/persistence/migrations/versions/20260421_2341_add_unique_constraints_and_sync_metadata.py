"""add_unique_constraints

Revision ID: 9d23bc5c3e6f
Revises: h1i2j3k4l5m6
Create Date: 2026-04-21 23:41:44.360739

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9d23bc5c3e6f'
down_revision: Union[str, None] = 'h1i2j3k4l5m6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint('uq_answer_participant_question', 'answers', ['participant_id', 'question_id'])
    op.create_unique_constraint('uq_feedback_participant_session', 'quiz_feedback', ['participant_id', 'session_id'])


def downgrade() -> None:
    op.drop_constraint('uq_feedback_participant_session', 'quiz_feedback', type_='unique')
    op.drop_constraint('uq_answer_participant_question', 'answers', type_='unique')
