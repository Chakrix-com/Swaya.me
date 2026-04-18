"""add one_word question type

Revision ID: f7a8b9c0d1e2
Revises: e3f4a5b6c7d8
Create Date: 2026-04-18 10:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE questions MODIFY COLUMN question_type "
        "ENUM('mcq','word_cloud','single_line','scale','paragraph','one_word') "
        "NOT NULL DEFAULT 'mcq'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE questions MODIFY COLUMN question_type "
        "ENUM('mcq','word_cloud','single_line','scale','paragraph') "
        "NOT NULL DEFAULT 'mcq'"
    )
