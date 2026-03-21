"""Add quiz_type to quizzes

Revision ID: z1a2b3c4d5e6
Revises: v1w2x3y4z5a6
Create Date: 2026-03-07 12:00:00.000000
"""
from alembic import op


revision = 'z1a2b3c4d5e6'
down_revision = 'v1w2x3y4z5a6'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE quizzes "
        "ADD COLUMN quiz_type ENUM('quiz','poll') NOT NULL DEFAULT 'quiz'"
    )


def downgrade():
    op.execute("ALTER TABLE quizzes DROP COLUMN quiz_type")
