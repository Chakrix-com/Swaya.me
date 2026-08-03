"""add provision_failed to code_workspaces.status enum

Revision ID: 20260803_0417
Revises: 20260802_1600
Create Date: 2026-08-03 04:17:00
"""
from alembic import op

revision = '20260803_0417'
down_revision = '20260802_1600'
branch_labels = None
depends_on = None

# CodeWorkspaceStatus's SQLAlchemy column has values_callable=lambda obj: [e.value
# for e in obj] (persistence/models/quiz.py), so it resolves DB values against
# Python's enum .value (lowercase), not .name — matching the original column
# definition in 20260724_1000_add_coding_challenge.py. Unlike TierEnum (see
# 20260802_1600), this one must stay lowercase.
_STATUS_ENUM_WITH_FAILED = (
    "ENUM('provisioning','active','submitted','abandoned','destroyed','provision_failed')"
)
_STATUS_ENUM_WITHOUT_FAILED = (
    "ENUM('provisioning','active','submitted','abandoned','destroyed')"
)


def upgrade():
    op.execute(
        "ALTER TABLE code_workspaces "
        "MODIFY COLUMN status "
        f"{_STATUS_ENUM_WITH_FAILED} NOT NULL DEFAULT 'provisioning'"
    )


def downgrade():
    op.execute(
        "ALTER TABLE code_workspaces "
        "MODIFY COLUMN status "
        f"{_STATUS_ENUM_WITHOUT_FAILED} NOT NULL DEFAULT 'provisioning'"
    )
