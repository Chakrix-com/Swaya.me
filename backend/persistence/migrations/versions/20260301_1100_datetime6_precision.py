"""Increase DateTime precision to 6 (microseconds) for timing columns

Revision ID: s3t4u5v6w7x8
Revises: r2s3t4u5v6w7
Create Date: 2026-03-01 11:00:00.000000

Alters:
  - session_question_timings.opened_at  DATETIME → DATETIME(6)
  - session_question_timings.closed_at  DATETIME → DATETIME(6)
  - answers.created_at                  DATETIME → DATETIME(6)

This allows sub-second (microsecond) precision for per-question timing deltas.
"""
from alembic import op


revision = 's3t4u5v6w7x8'
down_revision = 'r2s3t4u5v6w7'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE session_question_timings "
        "MODIFY opened_at DATETIME(6) NOT NULL, "
        "MODIFY closed_at DATETIME(6) NULL"
    )
    op.execute(
        "ALTER TABLE answers "
        "MODIFY created_at DATETIME(6) NOT NULL"
    )


def downgrade():
    op.execute(
        "ALTER TABLE session_question_timings "
        "MODIFY opened_at DATETIME NOT NULL, "
        "MODIFY closed_at DATETIME NULL"
    )
    op.execute(
        "ALTER TABLE answers "
        "MODIFY created_at DATETIME NOT NULL"
    )
