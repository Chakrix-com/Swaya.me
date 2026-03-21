"""Add single-line, scale, and paragraph question types

Revision ID: v1w2x3y4z5a6
Revises: u5v6w7x8y9z0
Create Date: 2026-03-07 05:10:00.000000
"""
from alembic import op


revision = 'v1w2x3y4z5a6'
down_revision = 'u5v6w7x8y9z0'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE questions "
        "MODIFY COLUMN question_type ENUM('mcq','word_cloud','single_line','scale','paragraph') "
        "NOT NULL DEFAULT 'mcq'"
    )
    op.execute("ALTER TABLE answers MODIFY COLUMN text_answer TEXT NULL")


def downgrade():
    op.execute(
        "ALTER TABLE questions "
        "MODIFY COLUMN question_type ENUM('mcq','word_cloud') "
        "NOT NULL DEFAULT 'mcq'"
    )
    op.execute("ALTER TABLE answers MODIFY COLUMN text_answer VARCHAR(100) NULL")
