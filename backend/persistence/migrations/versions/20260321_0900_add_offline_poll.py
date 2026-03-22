"""add offline poll support

Revision ID: a1b2c3d4e5f6
Revises: b8c7d6e5f4a3
Create Date: 2026-03-21 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME as MYSQL_DATETIME


# revision identifiers, used by Alembic.
revision: str = "f0e1d2c3b4a5"
down_revision: Union[str, None] = "b8c7d6e5f4a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. Alter quiz_type ENUM to add 'offline_poll'
    # MySQL requires listing ALL enum values when modifying
    bind.execute(sa.text(
        "ALTER TABLE quizzes MODIFY COLUMN quiz_type "
        "ENUM('quiz','poll','offline_poll') NOT NULL DEFAULT 'quiz'"
    ))

    quiz_columns = {col["name"] for col in inspector.get_columns("quizzes")}

    # 2. Add poll_slug column
    if "poll_slug" not in quiz_columns:
        op.add_column("quizzes", sa.Column("poll_slug", sa.String(64), nullable=True))
        op.create_index("ix_quizzes_poll_slug", "quizzes", ["poll_slug"], unique=True)

    # 3. Add offline date/time columns
    if "offline_start_at" not in quiz_columns:
        op.add_column("quizzes", sa.Column("offline_start_at", MYSQL_DATETIME(fsp=6), nullable=True))

    if "offline_end_at" not in quiz_columns:
        op.add_column("quizzes", sa.Column("offline_end_at", MYSQL_DATETIME(fsp=6), nullable=True))

    # 4. Add results email column
    if "offline_results_email" not in quiz_columns:
        op.add_column("quizzes", sa.Column("offline_results_email", sa.String(255), nullable=True))

    # 5. Add offline_session_id FK
    if "offline_session_id" not in quiz_columns:
        op.add_column("quizzes", sa.Column("offline_session_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_quizzes_offline_session_id",
            "quizzes",
            "quiz_sessions",
            ["offline_session_id"],
            ["id"],
        )

    # 6. Add completed_at to participants
    participant_columns = {col["name"] for col in inspector.get_columns("participants")}
    if "completed_at" not in participant_columns:
        op.add_column("participants", sa.Column("completed_at", MYSQL_DATETIME(fsp=6), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    participant_columns = {col["name"] for col in inspector.get_columns("participants")}
    if "completed_at" in participant_columns:
        op.drop_column("participants", "completed_at")

    quiz_columns = {col["name"] for col in inspector.get_columns("quizzes")}

    if "offline_session_id" in quiz_columns:
        op.drop_constraint("fk_quizzes_offline_session_id", "quizzes", type_="foreignkey")
        op.drop_column("quizzes", "offline_session_id")

    if "offline_results_email" in quiz_columns:
        op.drop_column("quizzes", "offline_results_email")

    if "offline_end_at" in quiz_columns:
        op.drop_column("quizzes", "offline_end_at")

    if "offline_start_at" in quiz_columns:
        op.drop_column("quizzes", "offline_start_at")

    if "poll_slug" in quiz_columns:
        op.drop_index("ix_quizzes_poll_slug", "quizzes")
        op.drop_column("quizzes", "poll_slug")

    # Revert enum
    bind.execute(sa.text(
        "ALTER TABLE quizzes MODIFY COLUMN quiz_type "
        "ENUM('quiz','poll') NOT NULL DEFAULT 'quiz'"
    ))
