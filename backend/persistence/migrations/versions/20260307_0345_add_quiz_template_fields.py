"""Add template metadata fields to quizzes

Revision ID: u5v6w7x8y9z0
Revises: t4u5v6w7x8y9
Create Date: 2026-03-07 03:45:00.000000
"""
from alembic import op


revision = 'u5v6w7x8y9z0'
down_revision = 't4u5v6w7x8y9'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE quizzes "
        "ADD COLUMN is_template BOOLEAN NOT NULL DEFAULT 0, "
        "ADD COLUMN template_scope ENUM('tenant','global') NOT NULL DEFAULT 'tenant'"
    )


def downgrade():
    op.execute("ALTER TABLE quizzes DROP COLUMN template_scope")
    op.execute("ALTER TABLE quizzes DROP COLUMN is_template")
