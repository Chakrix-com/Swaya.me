"""add exam type

Revision ID: a2b3c4d5e6f7
Revises: f0e1d2c3b4a5
Create Date: 2026-03-22 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME as MYSQL_DATETIME


# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "f0e1d2c3b4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. Alter quiz_type ENUM to add 'exam'
    bind.execute(sa.text(
        "ALTER TABLE quizzes MODIFY COLUMN quiz_type "
        "ENUM('quiz','poll','offline_poll','exam') NOT NULL DEFAULT 'quiz'"
    ))

    quiz_columns = {col["name"] for col in inspector.get_columns("quizzes")}

    # 2. Add exam_slug column
    if "exam_slug" not in quiz_columns:
        op.add_column("quizzes", sa.Column("exam_slug", sa.String(64), nullable=True))
        op.create_index("ix_quizzes_exam_slug", "quizzes", ["exam_slug"], unique=True)

    # 3. Add exam date/time columns
    if "exam_start_at" not in quiz_columns:
        op.add_column("quizzes", sa.Column("exam_start_at", MYSQL_DATETIME(fsp=6), nullable=True))

    if "exam_end_at" not in quiz_columns:
        op.add_column("quizzes", sa.Column("exam_end_at", MYSQL_DATETIME(fsp=6), nullable=True))

    # 4. Add exam time limit
    if "exam_time_limit_seconds" not in quiz_columns:
        op.add_column("quizzes", sa.Column("exam_time_limit_seconds", sa.Integer(), nullable=True))

    # 5. Add exam_session_id FK
    if "exam_session_id" not in quiz_columns:
        op.add_column("quizzes", sa.Column("exam_session_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_quizzes_exam_session_id",
            "quizzes",
            "quiz_sessions",
            ["exam_session_id"],
            ["id"],
        )

    # 6. Add exam results email
    if "exam_results_email" not in quiz_columns:
        op.add_column("quizzes", sa.Column("exam_results_email", sa.String(255), nullable=True))

    # 7. Add negative_points to questions
    question_columns = {col["name"] for col in inspector.get_columns("questions")}
    if "negative_points" not in question_columns:
        op.add_column("questions", sa.Column(
            "negative_points", sa.Integer(), nullable=False,
            server_default="0"
        ))

    # 8. Add exam participant fields
    participant_columns = {col["name"] for col in inspector.get_columns("participants")}
    if "started_at" not in participant_columns:
        op.add_column("participants", sa.Column("started_at", MYSQL_DATETIME(fsp=6), nullable=True))

    if "last_activity_at" not in participant_columns:
        op.add_column("participants", sa.Column("last_activity_at", MYSQL_DATETIME(fsp=6), nullable=True))

    if "is_abandoned" not in participant_columns:
        op.add_column("participants", sa.Column(
            "is_abandoned", sa.Boolean(), nullable=False, server_default="0"
        ))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    participant_columns = {col["name"] for col in inspector.get_columns("participants")}
    if "is_abandoned" in participant_columns:
        op.drop_column("participants", "is_abandoned")
    if "last_activity_at" in participant_columns:
        op.drop_column("participants", "last_activity_at")
    if "started_at" in participant_columns:
        op.drop_column("participants", "started_at")

    question_columns = {col["name"] for col in inspector.get_columns("questions")}
    if "negative_points" in question_columns:
        op.drop_column("questions", "negative_points")

    quiz_columns = {col["name"] for col in inspector.get_columns("quizzes")}
    if "exam_results_email" in quiz_columns:
        op.drop_column("quizzes", "exam_results_email")

    if "exam_session_id" in quiz_columns:
        op.drop_constraint("fk_quizzes_exam_session_id", "quizzes", type_="foreignkey")
        op.drop_column("quizzes", "exam_session_id")

    if "exam_time_limit_seconds" in quiz_columns:
        op.drop_column("quizzes", "exam_time_limit_seconds")

    if "exam_end_at" in quiz_columns:
        op.drop_column("quizzes", "exam_end_at")

    if "exam_start_at" in quiz_columns:
        op.drop_column("quizzes", "exam_start_at")

    if "exam_slug" in quiz_columns:
        op.drop_index("ix_quizzes_exam_slug", "quizzes")
        op.drop_column("quizzes", "exam_slug")

    # Revert enum
    bind.execute(sa.text(
        "ALTER TABLE quizzes MODIFY COLUMN quiz_type "
        "ENUM('quiz','poll','offline_poll') NOT NULL DEFAULT 'quiz'"
    ))
