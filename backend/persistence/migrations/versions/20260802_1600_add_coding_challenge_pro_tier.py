"""add coding_challenge_pro tier + per-user tier_override column

Revision ID: 20260802_1600
Revises: 20260729_1100
Create Date: 2026-08-02 16:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '20260802_1600'
down_revision = '20260729_1100'
branch_labels = None
depends_on = None

# TierEnum's SQLAlchemy column (persistence/models/core.py) has no
# values_callable, so it resolves DB values against Python's enum *names*
# (uppercase), not .value (lowercase) — see the original
# 20260208_0113_initial_schema.py, which declared this same column as
# ENUM('FREE','BASIC','PRO','ENTERPRISE'). Using lowercase labels here would
# desync every tenant/tier read app-wide (LookupError on every login).
_TIER_ENUM_WITH_CCP = (
    "ENUM('FREE','BASIC','PRO','ENTERPRISE','CODING_CHALLENGE_PRO')"
)
_TIER_ENUM_WITHOUT_CCP = "ENUM('FREE','BASIC','PRO','ENTERPRISE')"


def upgrade():
    op.execute(
        "ALTER TABLE tenants "
        "MODIFY COLUMN tier "
        f"{_TIER_ENUM_WITH_CCP} NOT NULL DEFAULT 'FREE'"
    )
    op.execute(
        "ALTER TABLE tier_configurations "
        "MODIFY COLUMN tier "
        f"{_TIER_ENUM_WITH_CCP} NOT NULL"
    )
    op.add_column(
        'users',
        sa.Column(
            'tier_override',
            sa.Enum('FREE', 'BASIC', 'PRO', 'ENTERPRISE', 'CODING_CHALLENGE_PRO', name='tierenum'),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column('users', 'tier_override')
    op.execute(
        "ALTER TABLE tier_configurations "
        "MODIFY COLUMN tier "
        f"{_TIER_ENUM_WITHOUT_CCP} NOT NULL"
    )
    op.execute(
        "ALTER TABLE tenants "
        "MODIFY COLUMN tier "
        f"{_TIER_ENUM_WITHOUT_CCP} NOT NULL DEFAULT 'FREE'"
    )
